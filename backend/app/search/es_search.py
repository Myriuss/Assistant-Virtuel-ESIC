# app/search/es_search.py
from typing import Any, Dict, List
from elasticsearch import Elasticsearch
from app.search.es_client import INDEX

def search_kb_by_type(es: Elasticsearch, query: str, doc_types: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^4", "content"],
                            "fuzziness": "AUTO",
                            "operator": "and"
                        }
                    }
                ],
                "filter": [
                    {"terms": {"doc_type": doc_types}}
                ]
            }
        }
    }
    res = es.search(index=INDEX, body=body)
    return res.get("hits", {}).get("hits", [])


def search_kb(es: Elasticsearch, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Wrapper pour compatibilité avec chat.py.
    Cherche dans tous les doc_types (sans filtre).
    """
    body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^4", "content"],
                "fuzziness": "AUTO",
                "operator": "and"
            }
        }
    }
    res = es.search(index=INDEX, body=body)
    return res.get("hits", {}).get("hits", [])
