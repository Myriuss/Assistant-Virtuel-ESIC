import json
import os
import sys
from typing import Any, Dict, Iterable, Optional

sys.path.append("/app")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Procedure

RAW_PATH = os.getenv("PROCEDURES_PATH", "/data/raw/procedures_esic.json")

TITLE_KEYS = {"title", "titre", "intitule", "intitulé", "procedure", "procédure", "nom"}
SUMMARY_KEYS = {"summary", "resume", "résumé", "description", "objectif"}
STEPS_KEYS = {"steps", "etapes", "étapes", "procedure_steps", "process"}

def _iter_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from _iter_dicts(it)

def _get_str(d: Dict[str, Any], keys: set) -> Optional[str]:
    for k in d.keys():
        if k in keys and isinstance(d.get(k), str):
            s = d[k].strip()
            return s if s else None
    lower = {k.lower(): k for k in d.keys()}
    for kk in keys:
        if kk.lower() in lower and isinstance(d.get(lower[kk.lower()]), str):
            s = d[lower[kk.lower()]].strip()
            return s if s else None
    return None

def _get_steps(d: Dict[str, Any]) -> Optional[Any]:
    for k in d.keys():
        if k in STEPS_KEYS and d.get(k) is not None:
            return d.get(k)
    lower = {k.lower(): k for k in d.keys()}
    for kk in STEPS_KEYS:
        if kk.lower() in lower:
            return d.get(lower[kk.lower()])
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
            title = _get_str(d, TITLE_KEYS)
            if not title:
                continue

            steps = _get_steps(d)
            summary = _get_str(d, SUMMARY_KEYS)

            db.add(Procedure(
                title=title,
                summary=summary,
                steps=steps if steps is not None else None,
                audience=d.get("audience") if isinstance(d.get("audience"), str) else None,
                language=(d.get("language") if isinstance(d.get("language"), str) else "fr"),
            ))
            inserted += 1

        db.commit()
        print(f"[OK] Procedures scan dicts: {scanned} | inserted: {inserted} | file: {RAW_PATH}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
