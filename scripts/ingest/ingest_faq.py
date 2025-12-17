import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.append("/app")  # backend est monté sur /app dans le container

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import FAQItem

RAW_PATH = os.getenv("FAQ_PATH", "/data/raw/faq_complete.json")

Q_KEYS = {"question", "q", "question_fr", "questionFR", "questionFr", "demande", "ask"}
A_KEYS = {"answer", "a", "reponse", "réponse", "reponse_fr", "answer_fr", "response", "réponse_fr"}
CAT_KEYS = {"category", "categorie", "cat", "theme", "thème"}
LANG_KEYS = {"language", "lang", "locale"}

def _iter_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    """Parcourt récursivement dict/list et yield chaque dict rencontré."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from _iter_dicts(it)

def _pick_first(d: Dict[str, Any], keys: set) -> Optional[str]:
    for k in d.keys():
        if k in keys and d.get(k) is not None:
            val = d.get(k)
            if isinstance(val, str):
                s = val.strip()
                return s if s else None
    # tentative “case-insensitive”
    lower = {k.lower(): k for k in d.keys()}
    for kk in keys:
        if kk.lower() in lower:
            val = d.get(lower[kk.lower()])
            if isinstance(val, str):
                s = val.strip()
                return s if s else None
    return None

def main():
    db: Session = SessionLocal()
    try:
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        inserted = 0
        scanned = 0
        for d in _iter_dicts(data):
            scanned += 1
            q = _pick_first(d, Q_KEYS)
            a = _pick_first(d, A_KEYS)

            if not q or not a:
                continue

            category = _pick_first(d, CAT_KEYS)
            language = _pick_first(d, LANG_KEYS) or "fr"
            tags = d.get("tags") if isinstance(d.get("tags"), list) else None

            db.add(FAQItem(
                question=q,
                answer=a,
                category=category,
                tags=tags,
                language=language
            ))
            inserted += 1

        db.commit()
        print(f"[OK] FAQ scan dicts: {scanned} | inserted: {inserted} | file: {RAW_PATH}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
