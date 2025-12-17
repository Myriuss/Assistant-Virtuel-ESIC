from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class FAQItem(Base):
    __tablename__ = "faq_items"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(120), nullable=True)
    tags = Column(JSON, nullable=True)          # liste de tags
    language = Column(String(10), default="fr") # fr/en
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    service = Column(String(160), nullable=False)
    name = Column(String(160), nullable=True)
    email = Column(String(160), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(160), nullable=True)
    hours = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Procedure(Base):
    __tablename__ = "procedures"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(240), nullable=False)
    summary = Column(Text, nullable=True)
    steps = Column(JSON, nullable=True)         # liste d'étapes
    audience = Column(String(120), nullable=True)
    language = Column(String(10), default="fr")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    id = Column(Integer, primary_key=True, index=True)
    program = Column(String(160), nullable=True)     # filière / promo
    group_name = Column(String(80), nullable=True)   # groupe
    course = Column(String(200), nullable=True)
    teacher = Column(String(160), nullable=True)
    room = Column(String(80), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    raw = Column(JSON, nullable=True)                # backup brut
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocChunk(Base):
    __tablename__ = "doc_chunks"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(200), nullable=False)     # nom du pdf
    section = Column(String(200), nullable=True)
    language = Column(String(10), default="fr")
    content = Column(Text, nullable=False)           # chunk text
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatEvent(Base):
    __tablename__ = "chat_events"
    id = Column(Integer, primary_key=True, index=True)
    user_hash = Column(String(80), nullable=False)   # hash/pseudo, pas PII
    channel = Column(String(40), default="web")      # web/kiosk
    user_message = Column(Text, nullable=False)
    detected_language = Column(String(10), nullable=True)
    intent = Column(String(80), nullable=True)
    entities = Column(JSON, nullable=True)
    response = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    resolved = Column(Boolean, default=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    chat_event_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)         # 1..5
    comment = Column(Text, nullable=True)
    corrected_answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
