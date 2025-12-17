from elasticsearch import Elasticsearch

ES_URL = "http://elasticsearch:9200"
INDEX = "kb_docs"

MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "fr_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "doc_type": {"type": "keyword"},   # faq / procedure / contact
            "db_id": {"type": "integer"},
            "title": {"type": "text", "analyzer": "fr_analyzer"},
            "content": {"type": "text", "analyzer": "fr_analyzer"},
            "tags": {"type": "keyword"},
            "language": {"type": "keyword"}
        }
    }
}

def main():
    es = Elasticsearch(ES_URL)
    if es.indices.exists(index=INDEX):
        es.indices.delete(index=INDEX)
    es.indices.create(index=INDEX, body=MAPPING)
    print(f"[OK] Created index: {INDEX}")

if __name__ == "__main__":
    main()
