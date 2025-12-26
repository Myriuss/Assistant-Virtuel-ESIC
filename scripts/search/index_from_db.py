import sys
sys.path.append("/app")

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import FAQItem, Procedure, Contact, TimetableSlot  # <-- import ajouté

ES_URL = "http://elasticsearch:9200"
INDEX = "kb_docs"


def buid_faq_content(f: FAQItem) -> str:
    parts = [
        f"Catégorie : {f.category_name} ({f.category_id})" if f.category_name and f.category_id else f.category_name or "",
        f"ID FAQ : {f.faq_id}" if f.faq_id else "",
        f"Question : {f.question}" if f.question else "",
        f"Réponse : {f.answer}" if f.answer else "",
    ]

    # Tags
    if f.tags:
        parts.append("Tags : " + ", ".join(map(str, f.tags)))

    # Documents associés
    if f.documents:
        parts.append("Documents associés : " + ", ".join(map(str, f.documents)))

    # Fréquence
    if f.frequency:
        parts.append(f"Fréquence : {f.frequency}")

    # Langue
    if f.language:
        parts.append(f"Langue : {f.language}")

    return "\n".join(p for p in parts if p)

def build_procedure_content(p: Procedure) -> str:
    summary = p.summary or ""

    steps_text = ""
    if p.steps:
        if isinstance(p.steps, list):
            steps_text = "\n".join(str(s) for s in p.steps)
        else:
            steps_text = str(p.steps)

    if summary and steps_text:
        return summary + "\n\nÉtapes :\n" + steps_text
    elif summary:
        return summary
    else:
        return steps_text


def build_contact_content(c: Contact) -> str:
    parts = [
        c.nom_complet,
        c.categorie_principale,
        c.sous_categorie,
        c.role,
        c.type_contact,
        c.email,
        c.telephone,
        c.batiment,
        c.bureau,
        c.horaires,
        c.formations_public,
        c.matieres_specialite,
        c.statut,
        c.commentaires,
    ]
    return " ".join(x for x in parts if x)


def build_timetable_content(t: TimetableSlot) -> str:
    day_str = t.day or t.start_time.strftime("%A")
    start_str = t.start_time.strftime("%Hh%M")
    end_str = t.end_time.strftime("%Hh%M")
    parts = [
        f"{day_str} {start_str}-{end_str}",
        t.program,
        t.group_name,
        t.subject_code,
        t.subject_name,
        t.course_type,
        t.teacher,
        t.room_name,
        t.room_code,
        t.building,
    ]
    return " ".join(p for p in parts if p)


def main():
    es = Elasticsearch(ES_URL)
    db: Session = SessionLocal()

    try:
        actions = []

        # FAQ
        for item in db.query(FAQItem).all():
            content = buid_faq_content(item)
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "faq",
                    "db_id": item.id,
                    "title": item.question,
                    "content": content,
                    "tags": item.tags or [],
                    "category_id": item.category_id,
                    "category_name": item.category_name,
                    "frequency": item.frequency,
                    "language": item.language or "fr",
                },
            })

        # Procédures
        for p in db.query(Procedure).all():
            content = build_procedure_content(p)
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "procedure",
                    "db_id": p.id,
                    "title": p.title,
                    "content": content,
                    "tags": [],
                    "language": p.language or "fr",
                },
            })

        # Contacts
        for c in db.query(Contact).all():
            content = build_contact_content(c)
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "contact",
                    "db_id": c.id,
                    "title": c.nom_complet or c.sous_categorie or c.categorie_principale,
                    "content": content,
                    "tags": [],
                    "language": "fr",
                },
            })

        # Emplois du temps
        for t in db.query(TimetableSlot).all():
            content = build_timetable_content(t)
            actions.append({
                "_op_type": "index",
                "_index": INDEX,
                "_source": {
                    "doc_type": "timetable",
                    "db_id": t.id,
                    "title": t.subject_name or t.subject_code or "",
                    "content": content,
                    "tags": [t.program, t.group_name] if t.program or t.group_name else [],
                    "language": "fr",
                },
            })

        if actions:
            bulk(es, actions, refresh=True)
        print(f"[OK] Indexed docs: {len(actions)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
