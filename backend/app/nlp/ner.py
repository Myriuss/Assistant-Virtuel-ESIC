import re
import spacy

_nlp = None

PROGRAM_ALIASES = {
    # B1
    "bachelor 1": "B1",
    "bachelor1": "B1",
    "b1": "B1",

    # B2
    "bachelor 2": "B2",
    "bachelor2": "B2",
    "b2": "B2",

    # B3 DEV
    "bachelor 3 developpement": "B3-DEV",
    "bachelor 3 développement": "B3-DEV",
    "bachelor 3 dev": "B3-DEV",
    "b3 dev": "B3-DEV",
    "b3 développement informatique": "B3-DEV",

    # B3 CYBER
    "bachelor 3 cybersecurite": "B3-CYBER",
    "bachelor 3 cybersécurité": "B3-CYBER",
    "b3 cyber": "B3-CYBER",
    "b3 cybersécurité": "B3-CYBER",

    # B3 DATA
    "bachelor 3 data": "B3-DATA",
    "bachelor 3 data science": "B3-DATA",
    "b3 data": "B3-DATA",

    # M1 IA
    "master 1": "M1-IA",
    "master 1 ia": "M1-IA",
    "m1 ia": "M1-IA",
    "master 1 intelligence artificielle": "M1-IA",
    "1ere annee de master ia": "M1-IA",
    "1ère année de master ia": "M1-IA",
    "data science 1e annee": "M1-IA",
    "data science 1ere annee": "M1-IA",
    "data science 1ère année": "M1-IA",

    # M2 IA
    "master 2": "M2-IA",
    "master 2 ia": "M2-IA",
    "m2 ia": "M2-IA",
    "master 2 intelligence artificielle": "M2-IA",
    "2eme annee de master ia": "M2-IA",
    "2ème année de master ia": "M2-IA",
    "data science 2e annee": "M2-IA",
    "data science 2eme annee": "M2-IA",
    "data science 2ème année": "M2-IA",
}

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

    # SERVICE
    service_hint = None
    for k in ["scolarité", "scolarite", "helpdesk", "informatique", "it",
              "comptabilité", "comptabilite", "administration", "bibliothèque", "bibliotheque"]:
        if k in low:
            if "scolar" in k:
                service_hint = "scolarite"
            elif "biblio" in k:
                service_hint = "bibliotheque"
            else:
                service_hint = k
            break

    # FORMATION (très simple : Data / Cybersécurité / Dev + année)
    formation = None
    m = re.search(r"(data science|cybersécurit[eé]|cybersecurite|développement|developpement).{0,15}([0-9](?:e|ème|eme)\s*ann[eé]e)", low)
    if m:
        formation = m.group(0).strip()
        normalized = (
            formation.lower()
            .replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("à", "a")
        ) if formation else None
    program_code = PROGRAM_ALIASES.get(formation) if formation else None
    # MATIERE / MODULE
    subject = None
    if "machine learning" in low:
        subject = "machine learning"
    elif "cybersécurité" in low or "cybersecurite" in low:
        subject = "cybersécurité"

    # DATE 
    dates = [e.text for e in doc.ents if e.label_ in {"DATE"}]
    # exemple simple pour "lundi prochain", "semaine prochaine"
    for kw in ["lundi prochain", "semaine prochaine", "demain"]:
        if kw in low and kw not in dates:
            dates.append(kw)

    return {
        "spacy": ents,
        "service_hint": service_hint,
        "formation": formation,
        "program_code": program_code,
        "subject": subject,
        "dates": dates,
    }
