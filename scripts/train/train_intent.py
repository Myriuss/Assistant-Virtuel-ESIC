import os
import sys
sys.path.append("/app")

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import joblib

from app.db.session import SessionLocal
from app.db.models import Contact, TimetableSlot, FAQItem

OUT_DIR = "/app/app/nlp/models"
OUT_PATH = f"{OUT_DIR}/intent.joblib"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    db: Session = SessionLocal()

    texts = []
    labels = []

    # -------- CONTACT --------
    for c in db.query(Contact).all():
        # phrase artificielle pour apprendre le pattern
        base = []
        if c.categorie_principale:
            base.append(c.categorie_principale)
        if c.sous_categorie:
            base.append(c.sous_categorie)
        if c.role:
            base.append(c.role)

        label_text = " ".join(base) if base else "contact campus"
        texts.append(f"contacter {label_text}")
        labels.append("contact")

    # Seeds pour contact
    contact_seeds = [
        "je veux joindre la scolarité",
        "comment contacter le service scolarité",
        "email du responsable de master IA",
        "numéro d'urgence du campus",
        "comment joindre l'infirmerie",
        "qui dois-je appeler en cas de problème sur le campus",
    ]
    for t in contact_seeds:
        texts.append(t)
        labels.append("contact")

    # -------- TIMETABLE --------
    for slot in db.query(TimetableSlot).all():
        parts = []
        if slot.program:
            parts.append(slot.program)
        if slot.group_name:
            parts.append(slot.group_name)
        if slot.subject_name:
            parts.append(slot.subject_name)

        label_text = " ".join(parts) if parts else "emploi du temps"
        texts.append(f"emploi du temps {label_text}")
        labels.append("timetable")

    # Seeds pour timetable
    timetable_seeds = [
        "emploi du temps",
        "mon planning de demain",
        "horaires des cours",
        "à quelle heure est mon cours de machine learning",
        "où est ma salle de TD",
    ]
    for t in timetable_seeds:
        texts.append(t)
        labels.append("timetable")

    # Entraînement
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X = vectorizer.fit_transform(texts)

    clf = LinearSVC()
    clf.fit(X, labels)

    payload = {
        "vectorizer": vectorizer,
        "clf": clf,
        "labels": sorted(set(labels)),
    }
    joblib.dump(payload, OUT_PATH)

    print(f"[OK] intent model saved: {OUT_PATH}")
    print(f"[INFO] labels: {sorted(set(labels))}")

    db.close()

if __name__ == "__main__":
    main()
