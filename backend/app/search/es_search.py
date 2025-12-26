from typing import Any, Dict, List, Tuple
from elasticsearch import Elasticsearch
from app.search.es_client import INDEX


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _boost_doc_type(query: str, doc_type: str) -> float:
    """
    Petit re-ranking métier (simple mais efficace).
    """
    q = _normalize(query)

    # Mots-clés "contact"
    contact_kw = ["contacter", "joindre", "appel", "appeler", "téléphone", "telephone", "mail", "email", "adresse", "horaire", "horaires", "ouvert", "ouverture"]
    # Mots-clés "planning"
    planning_kw = ["planning", "emploi du temps", "edt", "schedule"]
    # Mots-clés "certificat"
    cert_kw = ["certificat", "attestation", "scolarité", "inscription", "relevé", "releve"]

    boost = 0.0

    if any(k in q for k in contact_kw):
        if doc_type == "contact":
            boost += 1.5
        if doc_type == "procedure":
            boost += 0.4  # parfois procédure de contact
        if doc_type == "faq":
            boost += 0.2

    if any(k in q for k in planning_kw):
        if doc_type == "faq":
            boost += 1.0
        if doc_type == "procedure":
            boost += 0.4

    if any(k in q for k in cert_kw):
        # certificat/attestation -> souvent procédure ou FAQ, rarement contact générique
        if doc_type == "procedure":
            boost += 1.5
        if doc_type == "faq":
            boost += 0.8
        if doc_type == "contact":
            boost -= 0.5  # on pénalise contact ici

    return boost


def _rerank_hits(query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for h in hits:
        src = (h.get("_source") or {})
        dt = src.get("doc_type") or "kb"
        base = float(h.get("_score") or 0.0)
        final = base + _boost_doc_type(query, dt)
        scored.append((final, h))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored]


def search_kb_by_type(
    es: Elasticsearch,
    query: str,
    doc_types: List[str],
    top_k: int = 5,
    min_score: float = 2.5,
) -> List[Dict[str, Any]]:
    """
    Recherche avec filtre doc_type + seuil de score + re-ranking.
    """
    body = {
        "size": top_k,
        "min_score": min_score,
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"title": {"query": query, "boost": 5}}},
                    {"match_phrase": {"content": {"query": query, "boost": 2}}},
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^4", "content"],
                            "fuzziness": "AUTO",
                            "operator": "and"
                        }
                    },
                ],
                "minimum_should_match": 1,
                "filter": [{"terms": {"doc_type": doc_types}}],
            }
        },
    }
    res = es.search(index=INDEX, body=body)
    hits = res.get("hits", {}).get("hits", []) or []
    return _rerank_hits(query, hits)


def search_kb(
    es: Elasticsearch,
    query: str,
    top_k: int = 5,
    min_score: float = 2.5,
) -> List[Dict[str, Any]]:
    """
    Recherche globale (sans filtre doc_type) + seuil + re-ranking.
    """
    body = {
        "size": top_k,
        "min_score": min_score,
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"title": {"query": query, "boost": 5}}},
                    {"match_phrase": {"content": {"query": query, "boost": 2}}},
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^4", "content"],
                            "fuzziness": "AUTO",
                            "operator": "and"
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        },
    }
    res = es.search(index=INDEX, body=body)
    hits = res.get("hits", {}).get("hits", []) or []
    return _rerank_hits(query, hits)
