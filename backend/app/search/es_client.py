from elasticsearch import Elasticsearch
from app.core.config import settings

INDEX = "kb_docs"

def get_es() -> Elasticsearch:
    return Elasticsearch(settings.ELASTIC_URL)
