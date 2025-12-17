import os
import sys
sys.path.append("/app")

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import joblib

from app.db.session import SessionLocal
from app.db.models import FAQItem, Procedure, Contact

OUT_DIR = "/app/app/nlp/models"
OUT_PATH = f"{OUT_DIR}/intent.joblib"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    db: Session = SessionLocal()

    texts = []
    labels = []

    # FAQ
    for f in db.query(FAQItem).all():
        texts.append(f.question)
        labels.append("faq")

    # Procedures
    for p in db.query(Procedure).all():
        texts.append(p.title)
        labels.append("procedure")

    # Contacts
    for c in db.query(Contact).all():
        texts.append(f"contacter {c.service}")
        labels.append("contact")

    # Phrases génériques pour aider
    seeds = [
        ("emploi du temps", "timetable"),
        ("mon planning de demain", "timetable"),
        ("horaires des cours", "timetable"),
        ("règlement intérieur", "reglement"),
        ("code vestimentaire", "reglement"),
        ("sanction", "reglement"),
        ("je veux un certificat de scolarité", "procedure"),
        ("comment payer mes frais", "procedure"),
        ("je veux joindre la scolarité", "contact"),
    ]
    for t, lab in seeds:
        texts.append(t)
        labels.append(lab)

    # labels uniques
    unique_labels = sorted(set(labels))

    vectorizer = TfidfVectorizer(ngram_range=(1,2), min_df=1)
    X = vectorizer.fit_transform(texts)

    clf = LinearSVC()
    clf.fit(X, labels)

    payload = {"vectorizer": vectorizer, "clf": clf, "labels": unique_labels}
    joblib.dump(payload, OUT_PATH)

    print(f"[OK] intent model saved: {OUT_PATH}")
    print(f"[INFO] labels: {unique_labels}")

    db.close()

if __name__ == "__main__":
    main()
