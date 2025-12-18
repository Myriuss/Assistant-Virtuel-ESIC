FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Télécharge le modèle FR dans l'image (persistant)
RUN python -m spacy download fr_core_news_sm

COPY ./app ./app
