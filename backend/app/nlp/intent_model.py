from dataclasses import dataclass
from pathlib import Path
import joblib

MODEL_PATH = Path("/app/app/nlp/models/intent.joblib")

@dataclass
class IntentResult:
    intent: str
    confidence: float

def load_intent_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)

def predict_intent(model, text: str) -> IntentResult:
    # model = {"vectorizer": ..., "clf": ..., "labels": [...]}
    vect = model["vectorizer"]
    clf = model["clf"]
    labels = model["labels"]

    X = vect.transform([text])
    pred = clf.decision_function(X)

    # LinearSVC => decision scores (pas proba). On transforme en pseudo-confiance.
    import numpy as np
    if pred.ndim == 1:
        scores = pred
    else:
        scores = pred[0]

    best = int(np.argmax(scores))
    # pseudo confidence : sigmoid sur marge
    margin = float(scores[best])
    conf = 1 / (1 + np.exp(-margin))
    return IntentResult(intent=labels[best], confidence=float(conf))
