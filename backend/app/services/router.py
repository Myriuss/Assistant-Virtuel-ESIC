import re
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from unidecode import unidecode

from app.db.models import FAQItem, Procedure, Contact

STOPWORDS_FR = {
    "comment","pourquoi","quoi","que","qui","où","ou","quand","combien",
    "je","tu","il","elle","on","nous","vous","ils","elles",
    "puis","puis-je","peux","peux-tu","puisje","peuxje",
    "obtenir","faire","avoir","contacter","joindre",
    "la","le","les","un","une","des","du","de","d","à","a","au","aux",
    "et","ou","en","dans","sur","avec","sans","mon","ma","mes"
}

def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = unidecode(t)  # enlève les accents
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _keywords(query: str, max_kw: int = 6) -> List[str]:
    norm = _normalize(query)
    words = [w for w in norm.split(" ") if w and w not in STOPWORDS_FR and len(w) >= 3]
    # garde max_kw mots distincts, dans l’ordre
    seen = set()
    kws = []
    for w in words:
        if w not in seen:
            kws.append(w)
            seen.add(w)
        if len(kws) >= max_kw:
            break
    return kws

def _or_like(field, kws: List[str]):
    return or_(*[func.lower(field).like(f"%{kw}%") for kw in kws])

def search_faq(db: Session, query: str, limit: int = 5):
    kws = _keywords(query)
    if not kws:
        return []
    return (
        db.query(FAQItem)
        .filter(
            or_(
                _or_like(FAQItem.question, kws),
                _or_like(FAQItem.answer, kws),
                _or_like(FAQItem.category, kws),
            )
        )
        .limit(limit)
        .all()
    )

def search_procedures(db: Session, query: str, limit: int = 5):
    kws = _keywords(query)
    if not kws:
        return []
    return (
        db.query(Procedure)
        .filter(
            or_(
                _or_like(Procedure.title, kws),
                _or_like(Procedure.summary, kws),
            )
        )
        .limit(limit)
        .all()
    )

def search_contacts(db: Session, query: str, limit: int = 5):
    kws = _keywords(query)
    if not kws:
        return []
    return (
        db.query(Contact)
        .filter(
            or_(
                _or_like(Contact.service, kws),
                _or_like(Contact.name, kws),
                _or_like(Contact.email, kws),
            )
        )
        .limit(limit)
        .all()
    )
