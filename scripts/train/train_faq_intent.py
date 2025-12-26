import os
import sys
sys.path.append("/app")

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import joblib

from app.db.session import SessionLocal
from app.db.models import FAQItem

OUT_DIR = "/app/app/nlp/models"
OUT_PATH = f"{OUT_DIR}/faq.joblib"

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    db: Session = SessionLocal()

    texts = []
    labels = []

    # Chaque FAQ devient un exemple supervisé : question -> category_id
    for f in db.query(FAQItem).all():
        if not f.question:
            continue

        base = [f.question]

        # On enrichit avec tags et nom de catégorie pour plus de contexte
        if f.tags:
            base.extend([str(tag) for tag in f.tags])
        if f.category_name:
            base.append(f.category_name)

        text = " ".join(base)
        texts.append(text)
        labels.append(f.category_id)  # ex: "emploitemps", "proceduresadmin", ...

    # Sécurité : s'il n'y a pas assez de données
    if len(set(labels)) < 2:
        print("[WARN] Not enough distinct FAQ categories to train classifier")
        return

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

    print(f"[OK] FAQ category model saved: {OUT_PATH}")
    print(f"[INFO] FAQ categories: {sorted(set(labels))}")

    db.close()

if __name__ == "__main__":
    main()
