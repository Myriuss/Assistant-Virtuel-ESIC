import os

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://assistant:assistant@postgres:5432/assistant"
    )

    ELASTIC_URL: str = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")

settings = Settings()
