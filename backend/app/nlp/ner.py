import spacy

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("fr_core_news_sm")
    return _nlp

def extract_entities(text: str) -> dict:
    nlp = get_nlp()
    doc = nlp(text)

    ents = [{"text": e.text, "label": e.label_} for e in doc.ents]

    low = text.lower()
    service_hint = None
    for k in ["scolarité", "scolarite", "helpdesk", "informatique", "it", "comptabilité", "comptabilite", "administration"]:
        if k in low:
            service_hint = "scolarite" if "scolar" in k else k
            break

    return {"spacy": ents, "service_hint": service_hint}
