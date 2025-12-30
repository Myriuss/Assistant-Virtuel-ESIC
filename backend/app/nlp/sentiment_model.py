from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np

SENTIMENT_MODEL_PATH = Path("/app/app/nlp/models/sentiment.joblib")


@dataclass
class SentimentResult:
    label: str           # "neutre", "frustration", "urgent", "satisfaction"
    urgency_score: float # 0.0 à 1.0


def load_sentiment_model():
    if not SENTIMENT_MODEL_PATH.exists():
        return None
    return joblib.load(SENTIMENT_MODEL_PATH)


def predict_sentiment(model, text: str) -> SentimentResult:
    # modèle = Pipeline(tfidf + clf)
    proba = None
    if hasattr(model, "predict_proba"):
        # LogisticRegression
        proba = model.predict_proba([text])[0]
        labels = model.classes_
        best_idx = int(np.argmax(proba))
        label = str(labels[best_idx])
        # score d'urgence basé sur les proba
        p_urgent = proba[labels.tolist().index("urgent")] if "urgent" in labels else 0.0
        p_frustr = proba[labels.tolist().index("frustration")] if "frustration" in labels else 0.0
        urgency_score = float(p_urgent + 0.5 * p_frustr)

    else:
        # fallback : décision sans proba
        label = str(model.predict([text])[0])
        urgency_score = 0.8 if label in {"urgent", "frustration"} else 0.2

    urgency_score = max(0.0, min(1.0, urgency_score))
    return SentimentResult(label=label, urgency_score=urgency_score)
