import pandas as pd
from pathlib import Path
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

# Chemin ABSOLU dans le conteneur
DATA_PATH = Path("/data/raw/sentiments.csv")
MODEL_PATH = Path("/app/app/nlp/models/sentiment.joblib")


def main():
    df = pd.read_csv(DATA_PATH)
    texts = df["text"].astype(str).tolist()
    labels = df["label"].astype(str).tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
        )),
    ])

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Modèle sauvegardé dans {MODEL_PATH}")

if __name__ == "__main__":
    main()
