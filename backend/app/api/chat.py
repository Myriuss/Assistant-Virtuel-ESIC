import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ChatEvent, Feedback
from app.core.security import hash_user, looks_like_prompt_injection
from app.core.limiter import limiter

from app.search.es_client import get_es
from app.search.es_search import search_kb

from app.services.router import search_faq, search_procedures, search_contacts

from app.nlp.intent_model import load_intent_model, predict_intent
from app.nlp.ner import extract_entities

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
    language: Optional[str] = Field(default=None, description="fr|en (optionnel)")


class Source(BaseModel):
    type: str
    id: int
    title: str


class ChatResponse(BaseModel):
    answer: str
    intent: Optional[str]
    entities: Optional[dict]
    confidence: Optional[float]
    sources: list[Source]


class FeedbackRequest(BaseModel):
    chat_event_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    corrected_answer: Optional[str] = None


# Cache intent model (chargé 1 fois)
_INTENT_MODEL = None


def get_intent_model():
    global _INTENT_MODEL
    if _INTENT_MODEL is None:
        _INTENT_MODEL = load_intent_model()
    return _INTENT_MODEL


# ------------------------
# CHAT ENDPOINT
# ------------------------
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(
    payload: ChatRequest,
    request: Request,  # requis par slowapi
    db: Session = Depends(get_db),
):
    start = time.time()

    user_hash = hash_user(payload.user_id)
    msg = payload.message.strip()

    # 1) Sécurité : anti prompt injection basique
    if looks_like_prompt_injection(msg):
        raise HTTPException(
            status_code=400,
            detail="Requête rejetée (contenu suspect). Reformule ta question simplement."
        )

    # 2) NLP : intent + entities
    intent_model = get_intent_model()
    intent_pred = None
    intent_conf = None
    if intent_model:
        try:
            res = predict_intent(intent_model, msg)
            intent_pred = res.intent
            intent_conf = res.confidence
        except Exception:
            intent_pred = None
            intent_conf = None

    try:
        entities = extract_entities(msg)
    except Exception:
        entities = {}

    # Heuristique : détecter si l’utilisateur veut "contacter/joindre"
    q_low = msg.lower()
    wants_contact = any(w in q_low for w in ["contacter", "joindre", "email", "mail", "téléphone", "telephone", "appeler"])

    # ---------------------------------------------------------
    # Variables réponse
    # ---------------------------------------------------------
    answer = None
    sources: list[Source] = []

    final_intent = intent_pred  # intent "ML" par défaut
    final_confidence = intent_conf  # confiance "ML" par défaut

    # ---------------------------------------------------------
    # 3) Elasticsearch (prioritaire) + sélection du meilleur hit
    # ---------------------------------------------------------
    hits = []
    try:
        es = get_es()
        hits = search_kb(es, msg, top_k=5) or []
    except Exception:
        hits = []

    if hits:
        # Si demande "contact", on préfère un doc_type contact/procedure si disponible
        preferred = None
        if wants_contact or (entities.get("service_hint") is not None):
            for h in hits:
                dt = (h.get("_source", {}) or {}).get("doc_type")
                if dt in ("contact", "procedure"):
                    preferred = h
                    break

        h = preferred or hits[0]
        src = h.get("_source", {}) or {}

        doc_type = src.get("doc_type") or "kb"
        db_id = src.get("db_id") or 0
        title = src.get("title", "") or ""
        content = src.get("content", "") or ""

        # Confiance Elastic -> pseudo
        score = float(h.get("_score") or 0.0)
        es_conf = min(0.95, 0.55 + score / 10.0)

        # Si le modèle intent n’existe pas, on prend doc_type comme intent.
        # Sinon, on garde l'intent ML mais si Elastic est très confiant on peut l’utiliser.
        if final_intent is None or es_conf >= 0.85:
            final_intent = doc_type
            final_confidence = es_conf
        else:
            # si intent ML existe mais Elastic donne un doc_type cohérent, on peut garder ML.
            # on garde final_confidence = intent_conf
            pass

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
            answer = f"{title}\n\n{content}".strip()
            sources = [Source(type="kb", id=int(db_id), title=title)]

    # ---------------------------------------------------------
    # 4) Fallback DB (si Elastic ne donne rien)
    # ---------------------------------------------------------
    if not answer:
        faq = search_faq(db, msg, limit=3)
        if faq:
            final_intent = final_intent or "faq"
            final_confidence = final_confidence or 0.70
            answer = faq[0].answer
            sources = [Source(type="faq", id=faq[0].id, title=faq[0].question)]

    if not answer:
        procs = search_procedures(db, msg, limit=3)
        if procs:
            p = procs[0]
            final_intent = final_intent or "procedure"
            final_confidence = final_confidence or 0.65
            answer = f"{p.title}\n\n{p.summary or ''}".strip()
            sources = [Source(type="procedure", id=p.id, title=p.title)]

    if not answer:
        cons = search_contacts(db, msg, limit=3)
        if cons:
            c = cons[0]
            final_intent = final_intent or "contact"
            final_confidence = final_confidence or 0.60
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
            sources = [Source(type="contact", id=c.id, title=c.service)]

    # ---------------------------------------------------------
    # 5) Ultimate fallback (clarification)
    # ---------------------------------------------------------
    if not answer:
        final_intent = final_intent or "fallback"
        final_confidence = final_confidence or 0.20
        answer = (
            "Je n’ai pas trouvé une réponse certaine.\n"
            "Peux-tu préciser : (1) le sujet, (2) ta formation/promo, (3) une date si c’est lié au planning ?"
        )

    latency_ms = int((time.time() - start) * 1000)

    # ---------------------------------------------------------
    # 6) Log obligatoire
    # ---------------------------------------------------------
    event = ChatEvent(
        user_hash=user_hash,
        channel=payload.channel,
        user_message=msg,
        detected_language=payload.language,
        intent=final_intent,
        entities=entities,
        response=answer,
        confidence=final_confidence,
        resolved=(final_intent != "fallback"),
        latency_ms=latency_ms,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return ChatResponse(
        answer=answer,
        intent=final_intent,
        entities=entities,
        confidence=final_confidence,
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
