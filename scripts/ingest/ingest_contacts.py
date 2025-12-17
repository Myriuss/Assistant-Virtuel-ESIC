import json
import os
import sys
from typing import Any, Dict, Iterable, Optional

sys.path.append("/app")

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Contact

RAW_PATH = os.getenv("CONTACTS_PATH", "/data/raw/annuaire_contacts.json")

SERVICE_KEYS = {"service", "departement", "department", "pole", "pôle", "bureau", "direction"}
NAME_KEYS = {"name", "nom", "contact", "responsable"}
EMAIL_KEYS = {"email", "mail"}
PHONE_KEYS = {"phone", "tel", "telephone", "téléphone", "mobile"}
LOC_KEYS = {"location", "lieu", "bureau", "adresse"}
HOURS_KEYS = {"hours", "horaires", "horaire"}

def _iter_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from _iter_dicts(it)

def _get(d: Dict[str, Any], keys: set) -> Optional[str]:
    for k in list(d.keys()):
        if k in keys and d.get(k) is not None:
            v = d.get(k)
            if isinstance(v, str):
                s = v.strip()
                return s if s else None
    # case-insensitive
    lower = {k.lower(): k for k in d.keys()}
    for kk in keys:
        if kk.lower() in lower:
            v = d.get(lower[kk.lower()])
            if isinstance(v, str):
                s = v.strip()
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
            service = _get(d, SERVICE_KEYS)
            email = _get(d, EMAIL_KEYS)
            phone = _get(d, PHONE_KEYS)

            # on insère si au moins service + (email ou phone) existent
            if not service or (not email and not phone):
                continue

            db.add(Contact(
                service=service,
                name=_get(d, NAME_KEYS),
                email=email,
                phone=phone,
                location=_get(d, LOC_KEYS),
                hours=_get(d, HOURS_KEYS),
            ))
            inserted += 1

        db.commit()
        print(f"[OK] Contacts scan dicts: {scanned} | inserted: {inserted} | file: {RAW_PATH}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
