from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import hash_user
from app.db.session import SessionLocal
from app.db.models import ChatEvent, Feedback

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ForgetRequest(BaseModel):
    user_id: str = Field(..., description="Identifiant utilisateur (sera hashé).")


class ExportResponse(BaseModel):
    user_hash: str
    exported_at: datetime
    chat_events: List[Dict[str, Any]]
    feedback: List[Dict[str, Any]]


@router.post("/forget")
def forget(payload: ForgetRequest, db: Session = Depends(get_db)):
    uhash = hash_user(payload.user_id)

    events = db.query(ChatEvent).filter(ChatEvent.user_hash == uhash).all()
    if not events:
        return {"status": "ok", "deleted_chat_events": 0, "deleted_feedback": 0}

    event_ids = [e.id for e in events]

    deleted_feedback = (
        db.query(Feedback)
        .filter(Feedback.chat_event_id.in_(event_ids))
        .delete(synchronize_session=False)
    )

    deleted_events = (
        db.query(ChatEvent)
        .filter(ChatEvent.id.in_(event_ids))
        .delete(synchronize_session=False)
    )

    db.commit()
    return {
        "status": "ok",
        "deleted_chat_events": int(deleted_events or 0),
        "deleted_feedback": int(deleted_feedback or 0),
    }


@router.get("/export", response_model=ExportResponse)
def export_data(
    user_id: str = Query(..., description="Identifiant utilisateur (sera hashé)."),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    uhash = hash_user(user_id)

    events = (
        db.query(ChatEvent)
        .filter(ChatEvent.user_hash == uhash)
        .order_by(ChatEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    event_ids = [e.id for e in events]

    feedback = []
    if event_ids:
        fb_rows = (
            db.query(Feedback)
            .filter(Feedback.chat_event_id.in_(event_ids))
            .order_by(Feedback.created_at.desc())
            .all()
        )
        feedback = [
            {
                "id": f.id,
                "chat_event_id": f.chat_event_id,
                "rating": f.rating,
                "comment": f.comment,
                "corrected_answer": f.corrected_answer,
                "created_at": f.created_at,
            }
            for f in fb_rows
        ]

    chat_events = [
        {
            "id": e.id,
            "channel": e.channel,
            "user_message": e.user_message,
            "detected_language": e.detected_language,
            "intent": e.intent,
            "entities": e.entities,
            "response": e.response,
            "confidence": e.confidence,
            "resolved": e.resolved,
            "latency_ms": e.latency_ms,
            "created_at": e.created_at,
        }
        for e in events
    ]

    return ExportResponse(
        user_hash=uhash,
        exported_at=datetime.utcnow(),
        chat_events=chat_events,
        feedback=feedback,
    )
