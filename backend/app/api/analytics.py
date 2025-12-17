from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ChatEvent, Feedback

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AnalyticsSummary(BaseModel):
    window_days: int
    total_chats: int
    resolved_rate: float
    fallback_rate: float
    avg_latency_ms: Optional[float] = None
    avg_confidence: Optional[float] = None
    feedback_count: int
    avg_rating: Optional[float] = None


class IntentCount(BaseModel):
    intent: str
    count: int


class UnresolvedEvent(BaseModel):
    id: int
    created_at: datetime
    channel: str
    user_message: str
    intent: Optional[str] = None
    confidence: Optional[float] = None


def _window_start(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    start = _window_start(days)
    q = db.query(ChatEvent).filter(ChatEvent.created_at >= start)

    total = q.count()
    if total == 0:
        return AnalyticsSummary(
            window_days=days,
            total_chats=0,
            resolved_rate=0.0,
            fallback_rate=0.0,
            avg_latency_ms=None,
            avg_confidence=None,
            feedback_count=0,
            avg_rating=None,
        )

    resolved = q.filter(ChatEvent.resolved.is_(True)).count()
    fallback = q.filter((ChatEvent.intent == "fallback") | (ChatEvent.resolved.is_(False))).count()

    avg_latency = db.query(func.avg(ChatEvent.latency_ms)).filter(ChatEvent.created_at >= start).scalar()
    avg_conf = db.query(func.avg(ChatEvent.confidence)).filter(ChatEvent.created_at >= start).scalar()

    fb_q = db.query(Feedback).filter(Feedback.created_at >= start)
    fb_count = fb_q.count()
    avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.created_at >= start).scalar()

    return AnalyticsSummary(
        window_days=days,
        total_chats=total,
        resolved_rate=round(resolved / total, 4),
        fallback_rate=round(fallback / total, 4),
        avg_latency_ms=float(avg_latency) if avg_latency is not None else None,
        avg_confidence=float(avg_conf) if avg_conf is not None else None,
        feedback_count=fb_count,
        avg_rating=float(avg_rating) if avg_rating is not None else None,
    )


@router.get("/top-intents", response_model=List[IntentCount])
def top_intents(
    days: int = Query(default=7, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    start = _window_start(days)

    rows = (
        db.query(ChatEvent.intent, func.count(ChatEvent.id).label("cnt"))
        .filter(ChatEvent.created_at >= start)
        .group_by(ChatEvent.intent)
        .order_by(desc("cnt"))
        .limit(limit)
        .all()
    )

    return [IntentCount(intent=(intent or "unknown"), count=int(cnt)) for intent, cnt in rows]


@router.get("/unresolved", response_model=List[UnresolvedEvent])
def unresolved(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    start = _window_start(days)

    rows = (
        db.query(ChatEvent)
        .filter(ChatEvent.created_at >= start)
        .filter((ChatEvent.intent == "fallback") | (ChatEvent.resolved.is_(False)))
        .order_by(ChatEvent.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        UnresolvedEvent(
            id=r.id,
            created_at=r.created_at,
            channel=r.channel,
            user_message=r.user_message[:300],
            intent=r.intent,
            confidence=r.confidence,
        )
        for r in rows
    ]
