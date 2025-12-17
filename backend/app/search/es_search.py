from typing import Any, Dict, List
from elasticsearch import Elasticsearch
from app.search.es_client import INDEX

def search_kb(es: Elasticsearch, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q = query.strip()

    # Heuristiques simples
    q_low = q.lower()
    wants_contact = any(w in q_low for w in ["contacter", "joindre", "email", "mail", "téléphone", "telephone", "appeler"])

    should_terms = []
    # boost scolarité
    if "scolar" in q_low:
        should_terms += [
            {"match": {"title": {"query": "scolarite", "boost": 5}}},
            {"match": {"content": {"query": "scolarite", "boost": 3}}},
        ]
    if wants_contact:
        should_terms += [
            {"match": {"title": {"query": "contact", "boost": 4}}},
            {"match": {"content": {"query": "email", "boost": 3}}},
            {"match": {"content": {"query": "telephone", "boost": 3}}},
            {"match": {"content": {"query": "tel", "boost": 2}}},
        ]

    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["title^4", "content"],
                            "fuzziness": "AUTO",
                            "operator": "and"
                        }
                    }
                ],
                "should": should_terms,
                "minimum_should_match": 0 if not should_terms else 1
            }
        }
    }

    res = es.search(index=INDEX, body=body)
    return res.get("hits", {}).get("hits", [])
