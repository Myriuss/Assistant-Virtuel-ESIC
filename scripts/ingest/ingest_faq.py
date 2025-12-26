import json
import os
import sys
from typing import Any, Dict, List

sys.path.append("/app")  # backend est monté sur /app dans le container

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import FAQItem

RAW_PATH = os.getenv("FAQ_PATH", "/data/raw/faq_complete.json")

def main():
    db: Session = SessionLocal()
    try:
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

        categories: List[Dict[str, Any]] = data.get("categories", [])

        inserted = 0

        for cat in categories:
            category_id = cat.get("id")            # ex: "emploi_temps"
            category_name = cat.get("nom")        # ex: "Emplois du temps & Planning"

            questions = cat.get("questions", [])
            if not isinstance(questions, list):
                continue

            for q in questions:
                faq_id = q.get("id")              # ex: "EDT001"
                question = q.get("question")
                answer = q.get("reponse") or q.get("réponse") or q.get("answer")

                if not question or not answer:
                    continue

                tags = q.get("tags") or []
                if not isinstance(tags, list):
                    tags = []

                documents = q.get("documentsassocies") or []
                if not isinstance(documents, list):
                    documents = []

                frequency = q.get("frequence") or "moyenne"

                # Ici on suppose pour l’instant uniquement la version FR
                language = "fr"

                item = FAQItem(
                    faq_id=faq_id,
                    category_id=category_id,
                    category_name=category_name,
                    question=question,
                    answer=answer,
                    tags=tags,
                    documents=documents,
                    frequency=frequency,
                    language=language,
                )
                db.add(item)
                inserted += 1

        db.commit()
        print(f"[OK] FAQ inserted: {inserted} | file: {RAW_PATH}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
