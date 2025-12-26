import re
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, date, time as time_, timedelta
from sqlalchemy import or_, func, cast, case,TEXT
from unidecode import unidecode

from app.db.models import FAQItem, Procedure, Contact, TimetableSlot

STOPWORDS_FR = {
    "comment","pourquoi","quoi","que","qui","où","ou","quand","combien",
    "je","tu","il","elle","on","nous","vous","ils","elles",
    "puis","puis-je","peux","peux-tu","puisje","peuxje",
    "obtenir","faire","avoir","contacter","joindre",
    "la","le","les","un","une","des","du","de","d","à","a","au","aux",
    "et","ou","en","dans","sur","avec","sans","mon","ma","mes"
}

JOURS_FR = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}
def _normalize(text: str) -> str:
    t = (text or "").lower()
    t = unidecode(t)  # enlève les accents
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _next_weekday(base: date, weekday: int) -> date:
    """Renvoie la date du prochain `weekday` (0=lundi..6=dimanche) à partir de base
       (si aujourd'hui est ce jour, on prend aujourd'hui)."""
    delta = (weekday - base.weekday()) % 7
    return base + timedelta(days=delta)

def _keywords(query: str, max_kw: int = 6) -> List[str]:
    norm = _normalize(query)
    words = [w for w in norm.split(" ") if w and w not in STOPWORDS_FR and len(w) >= 3]
    # garde max_kw mots distincts, dans l’ordre
    seen = set()
    kws = []
    for w in words:
        if w not in seen:
            kws.append(w)
            seen.add(w)
        if len(kws) >= max_kw:
            break
    return kws

def _or_like(field, kws: List[str]):
    return or_(*[func.lower(field).like(f"%{kw}%") for kw in kws])

def detect_semester_flags(text: str) -> dict[str, bool]:
    t = _normalize(text)
    return {
        "has_s1": ("semestre 1" in t) or (" s1" in t),
        "has_s2": ("semestre 2" in t) or (" s2" in t),
    }

def detect_period_flags(text: str) -> dict[str, bool]:
    t = _normalize(text)
    return {
        "has_vacances": "vacances" in t,
        "has_weekend": ("week-end" in t) or ("week end" in t) or ("samedi" in t) or ("dimanche" in t),
        "has_feries": ("jour férié" in t) or ("jours fériés" in t) or ("férié" in t) or ("fete du travail" in t),
    }

def detect_service_flags(text: str) -> dict[str, bool]:
    t = text.lower()
    return {
        "has_biblio": "bibliothèque" in t or "bibliotheque" in t,
        "has_resto_u": "restaurant universitaire" in t or "resto u" in t,
        "has_cafeteria": "cafétéria" in t or "cafeteria" in t,
        "has_parking": "parking" in t,
        "has_vpn": "vpn" in t,
        "has_ent": "ent" in t,
    }

def extract_query_signals(query: str) -> dict:
    sig = {}
    sig.update(detect_semester_flags(query))
    sig.update(detect_period_flags(query))
    sig.update(detect_service_flags(query))
    return sig
def search_faq(db: Session, query: str, limit: int = 5, category_id: str | None = None, order_by_frequency: bool = False,):
    # --- 0) match exact sur la question FAQ ---
    q_norm = _normalize(query)

    exact = (
        db.query(FAQItem)
        .filter(func.lower(FAQItem.question) == func.lower(query))
        .all()
    )
    if exact:
        return exact

    # --- 1) recherche classique par mots-clés ---
    kws = _keywords(query)
    if not kws:
        return []

    tags_str = cast(FAQItem.tags, TEXT)

    base_filter = or_(
        _or_like(FAQItem.question, kws),
        _or_like(FAQItem.answer, kws),
        _or_like(FAQItem.category_name, kws),
        _or_like(FAQItem.category_id, kws),
        _or_like(tags_str, kws),
    )

    q = db.query(FAQItem).filter(base_filter)

    if category_id:
        q = q.filter(FAQItem.category_id == category_id)

    if order_by_frequency:
        freq_order = case(
            (
                (FAQItem.frequency == "très élevée", 1),
                (FAQItem.frequency == "élevée", 2),
                (FAQItem.frequency == "moyenne", 3),
                (FAQItem.frequency == "faible", 4),
                (FAQItem.frequency == "très faible", 5),
            ),
            else_=6,
        )
        q = q.order_by(freq_order)

    results = q.limit(max(limit * 3, 15)).all()
    if not results:
        return []

    # --- 2) reranking par signaux ---
    signals_q = extract_query_signals(query)

    def faq_signals(faq: FAQItem) -> dict:
        txt = " ".join([
            faq.question or "",
            faq.answer or "",
            " ".join(faq.tags or []),
            faq.category_name or "",
            faq.category_id or "",
        ])
        sig = {}
        sig.update(detect_semester_flags(txt))
        sig.update(detect_period_flags(txt))
        sig.update(detect_service_flags(txt))
        return sig

    def score_faq(faq: FAQItem) -> int:
        sig_f = faq_signals(faq)
        score = 0

        # 0) Bonus de similarité question <-> question FAQ
        faq_q_norm = _normalize(faq.question or "")
        faq_a_norm = _normalize(faq.answer or "")
        for kw in kws:
            if kw in faq_q_norm:
                score -= 4  # bonus fort : mot dans la question
            elif kw in faq_a_norm:
                score -= 2  # bonus plus faible : mot dans la réponse

            # 0bis) Malus thématiques génériques
        faq_txt = _normalize((faq.question or "") + " " + (faq.answer or ""))
        q_txt = _normalize(query)

        # Exams
        q_mentions_exam = ("examen" in q_txt) or ("examens" in q_txt)
        faq_mentions_exam = ("examen" in faq_txt) or ("examens" in faq_txt)
        if faq_mentions_exam and not q_mentions_exam:
            score += 8  # malus fort

        # Absences
        q_mentions_absences = ("absence" in q_txt) or ("absences" in q_txt)
        faq_mentions_absences = ("absence" in faq_txt) or ("absences" in faq_txt)
        if q_mentions_absences and not faq_mentions_absences:
            score += 3
        if not q_mentions_absences and faq_mentions_absences:
            score += 2

        # Jours fériés
        q_mentions_feries = (
                "jour feri" in q_txt or "jours feri" in q_txt or "feries" in q_txt
        )
        faq_mentions_feries = (
                "jour feri" in faq_txt or "jours feri" in faq_txt or "feries" in faq_txt
        )
        if q_mentions_feries and not faq_mentions_feries:
            score += 3
        if not q_mentions_feries and faq_mentions_feries and "vacances" in faq_txt:
            score += 2

        # 1) Semestre S1 / S2
        q_has_s1, q_has_s2 = signals_q["has_s1"], signals_q["has_s2"]
        f_has_s1, f_has_s2 = sig_f["has_s1"], sig_f["has_s2"]

        if q_has_s1 or q_has_s2:
            if q_has_s1 and f_has_s1 and not f_has_s2:
                score -= 5
            if q_has_s2 and f_has_s2 and not f_has_s1:
                score -= 5
            if q_has_s1 and f_has_s2 and not f_has_s1:
                score += 5
            if q_has_s2 and f_has_s1 and not f_has_s2:
                score += 5

        # 2) Vacances / week-end / jours fériés (signaux globaux)
        for key in ["has_vacances", "has_weekend", "has_feries"]:
            if signals_q[key]:
                if sig_f[key]:
                    score -= 4
                else:
                    score += 2

        # 3) Services (biblio, ENT, etc.)
        for key in ["has_biblio", "has_resto_u", "has_cafeteria", "has_parking", "has_vpn", "has_ent"]:
            if signals_q[key]:
                if sig_f[key]:
                    score -= 4
                else:
                    score += 2

        return score

    results = sorted(results, key=score_faq)
    return results[:limit]
def search_procedures(db: Session, query: str, limit: int = 5):
    kws = _keywords(query)
    if not kws:
        return []
    return (
        db.query(Procedure)
        .filter(
            or_(
                _or_like(Procedure.title, kws),
                _or_like(Procedure.summary, kws),
            )
        )
        .limit(limit)
        .all()
    )

def search_contacts(db: Session, query: str, limit: int = 5):
    kws = _keywords(query)
    if not kws:
        return []

    q_low = query.lower()
    base_query = db.query(Contact).filter(
            or_(
                _or_like(Contact.nom_complet, kws),  # personnes (enseignants, responsables…)
                _or_like(Contact.categorie_principale, kws),  # Direction, Services étudiants, Urgences…
                _or_like(Contact.sous_categorie, kws),  # Scolarité, Bibliothèque, Infirmerie…
                _or_like(Contact.role, kws),  # Responsable Master IA, Infirmière, etc.
                _or_like(Contact.email, kws),
                _or_like(Contact.telephone, kws),
                _or_like(Contact.batiment, kws),
                _or_like(Contact.bureau, kws),
                _or_like(Contact.horaires, kws),
                _or_like(Contact.formations_public, kws),  # Master IA, Bachelor 3 Data…
                _or_like(Contact.matieres_specialite, kws),  # Machine Learning, Bibliothèque, etc.
                _or_like(Contact.commentaires, kws),  # missions, description service…
            )
        )
    # Cas spécial : questions sur la scolarité → on restreint aux services administratifs
    if "scolarité" in q_low or "scolarite" in q_low:
        base_query = base_query.filter(Contact.sous_categorie.ilike("%scolar%"))
    # Cas spécial : responsable de Master IA
    if "responsable" in q_low and ("master" in q_low and ("ia" in q_low or "intelligence artificielle" in q_low)):
        base_query = (
            base_query
            .filter(Contact.categorie_principale == "Responsables pédagogiques")
            .filter(
                or_(
                    Contact.formations_public.ilike("%master%ia%"),
                    Contact.formations_public.ilike("%master%intelligence artificielle%"),
                )
            )
        )

    return base_query.limit(limit).all()


def search_timetable(db: Session, query: str, program: str | None = None, group_name: str | None = None, limit: int = 10):
    q_low = query.lower()

    q = db.query(TimetableSlot)

    # filtres programme / groupe si fournis
    if program:
        q = q.filter(TimetableSlot.program == program)
    if group_name:
        q = q.filter(TimetableSlot.group_name == group_name)

    # Cas 1 : Machine Learning
    if "machine learning" in q_low:
        q = q.filter(
            or_(
                func.lower(TimetableSlot.subject_name).like("%machine learning%"),
                func.lower(TimetableSlot.subject_code).like("%ml%"),
            )
        )

    # Cas 2 : Cybersécurité
    elif "cybersecurite" in q_low or "cybersécurité" in q_low:
        q = q.filter(
            or_(
                func.lower(TimetableSlot.subject_name).like("%cybersecur%"),
                func.lower(TimetableSlot.subject_name).like("%cybersécur%")
            )
        )

        # si on parle de B3, renforcer sur B3
        if "b3" in q_low:
            q = q.filter(func.lower(TimetableSlot.program).like("%b3%"))

    # Cas 3 : autres questions d’emploi du temps (dont "Quels sont mes cours lundi ?")
    else:
        # pour l’instant, on renvoie simplement les premiers cours (planning global)
        # tu pourras plus tard filtrer par programme/groupe si l’utilisateur précise "B1-A", "B3-DATA", etc.
        pass

    return q.order_by(TimetableSlot.start_time).limit(limit).all()
