from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Date
from sqlalchemy.sql import func
from app.db.session import Base

class FAQItem(Base):
    __tablename__ = "faq_items"

    id = Column(Integer, primary_key=True, index=True)

    # ID fonctionnel de la FAQ (ex : "EDT001")
    faq_id = Column(String(20), nullable=False, unique=True, index=True)

    # Catégorie JSON (ex : "emploi_temps")
    category_id = Column(String(50), nullable=False)

    # Nom lisible de la catégorie (ex : "Emplois du temps & Planning")
    category_name = Column(String(150), nullable=False)

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    # liste de tags (tableau JSON de strings)
    tags = Column(JSON, nullable=False, default=list)

    # liste de documents associés (JSON de strings)
    documents = Column(JSON, nullable=False, default=list)

    # fréquence : "très élevée", "élevée", "moyenne", ...
    frequency = Column(String(20), nullable=False)

    language = Column(String(10), default="fr")  # fr/en

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)

    # Structure fonctionnelle
    categorie_principale = Column(String(80), nullable=False)
    sous_categorie = Column(String(160), nullable=True)
    role = Column(String(160), nullable=True)
    nom_complet = Column(String(160), nullable=True)
    type_contact = Column(String(50), nullable=False)

    # Coordonnées
    email = Column(String(160), nullable=True)
    telephone = Column(String(50), nullable=True)

    # Localisation détaillée
    batiment = Column(String(80), nullable=True)
    bureau = Column(String(80), nullable=True)

    # Disponibilité
    horaires = Column(String(160), nullable=True)

    # Périmètre pédagogique / cible
    formations_public = Column(String(160), nullable=True)
    matieres_specialite = Column(String(255), nullable=True)

    # Métadonnées
    statut = Column(String(50), nullable=True)
    commentaires = Column(String(255), nullable=True)

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

    program = Column(String(160), nullable=True)       # formation
    group_name = Column(String(80), nullable=True)     # groupe
    semester = Column(String(20), nullable=True)       # semestre
    exam_start = Column(Date, nullable=True)
    exam_end = Column(Date, nullable=True)

    subject_code = Column(String(50), nullable=True)   # matiere_code
    subject_name = Column(String(255), nullable=True)  # matiere_nom
    course_type = Column(String(20), nullable=True)    # type_cours (CM/TD/TP)

    teacher_id = Column(String(50), nullable=True)     # enseignant_id
    teacher = Column(String(160), nullable=True)       # enseignant_nom

    room_code = Column(String(80), nullable=True)      # salle_code
    room_name = Column(String(160), nullable=True)     # salle_nom
    building = Column(String(80), nullable=True)       # batiment

    day = Column(String(20), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    raw = Column(JSON, nullable=True)
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
