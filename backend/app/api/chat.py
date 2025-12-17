import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ChatEvent, Feedback
from app.core.security import hash_user, looks_like_prompt_injection
from app.services.router import search_faq, search_procedures, search_contacts
from app.core.limiter import limiter

from app.search.es_client import get_es
from app.search.es_search import search_kb

router = APIRouter()


# ------------------------
# DB dependency
# ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------
# Schemas
# ------------------------
class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant client (sera hashé)")
    message: str = Field(..., min_length=1, max_length=2000)
    channel: str = Field(default="web", description="web | kiosk")
    language: str | None = Field(default=None)


class Source(BaseModel):
    type: str
    id: int
    title: str


class ChatResponse(BaseModel):
    answer: str
    intent: str | None
    entities: dict | None
    confidence: float | None
    sources: list[Source]


class FeedbackRequest(BaseModel):
    chat_event_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
    corrected_answer: str | None = None


# ------------------------
# CHAT ENDPOINT
# ------------------------
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(
    payload: ChatRequest,
    request: Request,   # requis par slowapi
    db: Session = Depends(get_db),
):
    start = time.time()

    user_hash = hash_user(payload.user_id)
    msg = payload.message.strip()

    # Sécurité : détection basique prompt injection
    if looks_like_prompt_injection(msg):
        raise HTTPException(
            status_code=400,
            detail="Requête rejetée (contenu suspect). Reformule ta question simplement."
        )

    answer = None
    intent = None
    confidence = None
    sources: list[Source] = []

    # ---------------------------------------------------------
    # 0) Elasticsearch (prioritaire)
    # ---------------------------------------------------------
    hits = []
    try:
        es = get_es()
        hits = search_kb(es, msg, top_k=3)
    except Exception:
        hits = []

    if hits:
        q_low = msg.lower()
        wants_contact = any(
            w in q_low for w in ["contacter", "joindre", "email", "mail", "téléphone", "telephone", "appeler"])

        preferred = None
        if wants_contact:
            for h in hits:
                dt = (h.get("_source", {}) or {}).get("doc_type")
                if dt in ("contact", "procedure"):
                    preferred = h
                    break

        h = preferred or hits[0]
        src = h.get("_source", {})
        doc_type = src.get("doc_type")
        db_id = src.get("db_id")
        title = src.get("title", "")
        content = src.get("content", "")

        intent = doc_type or "kb"
        score = float(h.get("_score") or 0.0)
        confidence = min(0.95, 0.55 + score / 10.0)

        if doc_type == "faq":
            answer = content
            sources = [Source(type="faq", id=int(db_id), title=title)]

        elif doc_type == "procedure":
            answer = f"{title}\n\n{content}".strip()
            sources = [Source(type="procedure", id=int(db_id), title=title)]

        elif doc_type == "contact":
            answer = f"{title}\n\n{content}".strip()
            sources = [Source(type="contact", id=int(db_id), title=title)]

        else:
            # type inconnu : on renvoie quand même quelque chose
            answer = f"{title}\n\n{content}".strip()
            sources = [Source(type="kb", id=int(db_id) if db_id else 0, title=title)]

    # ---------------------------------------------------------
    # 1) Fallback DB (si Elastic ne donne rien)
    # ---------------------------------------------------------
    if not answer:
        faq = search_faq(db, msg, limit=3)
        if faq:
            intent = "faq"
            answer = faq[0].answer
            confidence = 0.70
            sources = [Source(type="faq", id=faq[0].id, title=faq[0].question)]

    if not answer:
        procs = search_procedures(db, msg, limit=3)
        if procs:
            p = procs[0]
            intent = "procedure"
            answer = f"{p.title}\n\n{p.summary or ''}".strip()
            confidence = 0.65
            sources = [Source(type="procedure", id=p.id, title=p.title)]

    if not answer:
        cons = search_contacts(db, msg, limit=3)
        if cons:
            c = cons[0]
            intent = "contact"
            lines = [f"Service : {c.service}"]
            if c.name:
                lines.append(f"Contact : {c.name}")
            if c.email:
                lines.append(f"Email : {c.email}")
            if c.phone:
                lines.append(f"Téléphone : {c.phone}")
            if c.location:
                lines.append(f"Lieu : {c.location}")
            if c.hours:
                lines.append(f"Horaires : {c.hours}")
            answer = "\n".join(lines)
            confidence = 0.60
            sources = [Source(type="contact", id=c.id, title=c.service)]

    # ---------------------------------------------------------
    # 2) Ultimate fallback
    # ---------------------------------------------------------
    if not answer:
        intent = "fallback"
        confidence = 0.20
        answer = (
            "Je n’ai pas trouvé une réponse certaine.\n"
            "Peux-tu préciser le sujet, ta formation/promo ou la date concernée ?"
        )

    latency_ms = int((time.time() - start) * 1000)

    # Log obligatoire
    event = ChatEvent(
        user_hash=user_hash,
        channel=payload.channel,
        user_message=msg,
        detected_language=payload.language,
        intent=intent,
        entities=None,
        response=answer,
        confidence=confidence,
        resolved=(intent != "fallback"),
        latency_ms=latency_ms,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return ChatResponse(
        answer=answer,
        intent=intent,
        entities=None,
        confidence=confidence,
        sources=sources,
    )


# ------------------------
# FEEDBACK
# ------------------------
@router.post("/feedback")
def feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    fb = Feedback(
        chat_event_id=payload.chat_event_id,
        rating=payload.rating,
        comment=payload.comment,
        corrected_answer=payload.corrected_answer,
    )
    db.add(fb)
    db.commit()
    return {"status": "ok"}
