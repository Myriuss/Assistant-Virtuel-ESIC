import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.append("/app")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Procedure

RAW_PATH = os.getenv("PROCEDURES_PATH", "/data/raw/procedures_esic.json")
SOURCE_NAME = os.path.basename(RAW_PATH)


def _safe_str(x: Any) -> Optional[str]:
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return None


def main() -> None:
    db: Session = SessionLocal()
    try:
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        procedures = payload.get("procedures", [])
        if not isinstance(procedures, list):
            raise ValueError("procedures_esic.json: 'procedures' doit être une liste")

        db.query(Procedure).delete(synchronize_session=False)

        inserted = 0
        for p in procedures:
            if not isinstance(p, dict):
                continue

            title = _safe_str(p.get("titre")) or _safe_str(p.get("title"))
            if not title:
                continue

            steps = p.get("etapes") if isinstance(p.get("etapes"), list) else None

            db.add(
                Procedure(
                    title=title,
                    summary=_safe_str(p.get("description")),
                    steps=steps,
                      audience=(', '.join([str(x) for x in p.get('public_concerne') if x]) if isinstance(p.get('public_concerne'), list) else _safe_str(p.get('public_concerne'))),
                    language="fr",
                )
            )
            inserted += 1

        db.commit()
        print(f"[OK] Procedures inserted: {inserted} | source: {SOURCE_NAME}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
