from dataclasses import dataclass
from pathlib import Path
import joblib
import numpy as np

INTENT_MODEL_PATH = Path("/app/app/nlp/models/intent.joblib")
FAQ_MODEL_PATH = Path("/app/app/nlp/models/faq.joblib")

# ------------ Intent global ------------
@dataclass
class IntentResult:
    intent: str
    confidence: float

def load_intent_model():
    if not INTENT_MODEL_PATH.exists():
        return None
    return joblib.load(INTENT_MODEL_PATH)

def predict_intent(model, text: str) -> IntentResult:
    # model = {"vectorizer": ..., "clf": ..., "labels": [...]}
    vect = model["vectorizer"]
    clf = model["clf"]
    labels = model["labels"]

    X = vect.transform([text])
    pred = clf.decision_function(X)

    # LinearSVC => decision scores (pas proba). On transforme en pseudo-confiance.
    if pred.ndim == 1:
        scores = pred
    else:
        scores = pred[0]

    best = int(np.argmax(scores))
    # pseudo confidence : sigmoid sur marge
    margin = float(scores[best])
    conf = 1 / (1 + np.exp(-margin))
    return IntentResult(intent=labels[best], confidence=float(conf))

# ------------ Catégorie FAQ ------------

@dataclass
class FAQCategoryResult:
    category_id: str
    confidence: float

def load_faq_model():
    if not FAQ_MODEL_PATH.exists():
        return None
    return joblib.load(FAQ_MODEL_PATH)

def predict_faq_category(model, text: str) -> FAQCategoryResult:
    vect = model["vectorizer"]
    clf = model["clf"]
    labels = model["labels"]

    X = vect.transform([text])
    pred = clf.decision_function(X)

    if pred.ndim == 1:
        scores = pred
    else:
        scores = pred[0]

    best = int(np.argmax(scores))
    margin = float(scores[best])
    conf = 1 / (1 + np.exp(-margin))
    return FAQCategoryResult(category_id=labels[best], confidence=float(conf))