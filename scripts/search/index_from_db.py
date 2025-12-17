import sys
sys.path.append("/app")

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import FAQItem, Procedure, Contact

ES_URL = "http://elasticsearch:9200"
INDEX = "kb_docs"

def main():
    es = Elasticsearch(ES_URL)
    db: Session = SessionLocal()

    try:
        actions = []

        for item in db.query(FAQItem).all():
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "faq",
                    "db_id": item.id,
                    "title": item.question,
                    "content": item.answer,
                    "tags": item.tags or [],
                    "language": item.language or "fr",
                }
            })

        for p in db.query(Procedure).all():
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "procedure",
                    "db_id": p.id,
                    "title": p.title,
                    "content": (p.summary or "") + "\n" + (str(p.steps) if p.steps else ""),
                    "tags": [],
                    "language": p.language or "fr",
                }
            })

        for c in db.query(Contact).all():
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "contact",
                    "db_id": c.id,
                    "title": c.service,
                    "content": " ".join([x for x in [c.name, c.email, c.phone, c.location, c.hours] if x]),
                    "tags": [],
                    "language": "fr",
                }
            })

        bulk(es, actions, refresh=True)
        print(f"[OK] Indexed docs: {len(actions)}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
