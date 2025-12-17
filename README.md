#  Assistant Virtuel Campus

## 1. Présentation du projet

L’**Assistant Virtuel Campus** est une API conversationnelle destinée à répondre aux questions des étudiants, visiteurs ou collaborateurs d’un établissement (scolarité, planning, procédures, contacts, FAQ, etc.).

Le projet est conçu comme un **service backend production-ready**, intégrant :
- une base de connaissance structurée (PostgreSQL),
- un moteur de recherche (Elasticsearch),
- des composants NLP (classification d’intention, NER),
- des mécanismes de sécurité et de conformité (rate limiting, GDPR),
- une stack complète d’observabilité (Prometheus, Grafana, Loki),
- un outil de BI pour l’analyse métier (Superset).

---

## 2. Architecture globale

```
Utilisateur
   |
   | HTTP (POST /chat)
   v
FastAPI (Backend)
   |
   |-- NLP (Intent + NER)
   |-- Recherche Elasticsearch
   |-- Fallback PostgreSQL
   |-- Logs & métriques
   |
   v
Réponse structurée (answer, intent, entities, confidence, sources)
```

---

## 3. Stack technique

| Brique | Technologie |
|------|------------|
| API | FastAPI (Python) |
| Base de données | PostgreSQL |
| Search | Elasticsearch |
| NLP | TF-IDF + SVM, spaCy |
| Observabilité | Prometheus, Grafana, Loki, Promtail |
| BI / Analytics | Apache Superset |
| Conteneurisation | Docker & Docker Compose |

---

## 4. Fonctionnalités principales

### API Conversationnelle
- `POST /chat`
  - réponse textuelle
  - intention détectée
  - entités extraites
  - score de confiance
  - sources (FAQ, procédure, contact)

### Analytics
- `GET /analytics/summary`
- `GET /analytics/top-intents`
- `GET /analytics/unresolved`

### GDPR / Conformité
- `GET /gdpr/export`
- `POST /gdpr/forget`

### Supervision
- `GET /health`
- `GET /metrics` (Prometheus)

---

## 5. Arborescence du projet

```
Assistant-virtuel-campus/
├── backend/
│   ├── app/
│   │   ├── api/            # chat, analytics, gdpr, health
│   │   ├── core/           # sécurité, rate limit, config
│   │   ├── db/             # modèles + session SQLAlchemy
│   │   ├── nlp/            # intent, NER
│   │   ├── search/         # Elasticsearch
│   │   ├── services/       # logique métier DB
│   │   └── main.py         # entrée FastAPI
│   ├── Dockerfile
│   └── requirements.txt
│
├── scripts/
│   ├── ingest/             # ingestion FAQ / contacts / procédures
│   └── train/              # entraînement NLP
│
├── observability/
│   ├── prometheus/
│   ├── loki/
│   └── promtail/
│
├── docker-compose.yml
└── README.md
```

---

## 6. Prérequis

- Docker Desktop
- Docker Compose v2
- Ports libres :
  - 8000 (API)
  - 5432 (PostgreSQL)
  - 9200 (Elasticsearch)
  - 3000 (Grafana)
  - 9090 (Prometheus)
  - 3100 (Loki)
  - 8088 (Superset)

---

## 7. Installation

### 1. Cloner le projet
```bash
git clone https://github.com/Myriuss/Assistant-Virtuel-ESIC
cd Assistant-virtuel-campus
```

### 2. Lancer tous les services
```bash
docker compose up -d --build
```

Le premier démarrage peut prendre plusieurs minutes.

---

## 8. Vérifications après installation

### Backend
```bash
curl http://localhost:8000/health
```

### Test du chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Je veux joindre la scolarité","channel":"web"}'
```

### Prometheus
- Accès : http://localhost:9090/targets
- Le backend doit être **UP**

### Grafana
- Accès : http://localhost:3000
- Identifiants par défaut :
  - user : admin
  - password : admin

Configurer les datasources : (add datasource)
- Prometheus → http://prometheus:9090
- Loki → http://loki:3100

### Logs (Grafana → Explore → Loki) 
```
{container=~".*av_backend.*"}
```

---

## 9. Observabilité

### Métriques
- volume de requêtes
- latence API
- erreurs HTTP
- métriques runtime Python

### Logs
- logs FastAPI
- erreurs applicatives
- événements système

---

## 10. Commandes utiles

```bash
docker compose ps
docker compose logs backend
docker compose restart backend
docker compose down
```

---

## 11. Dépannage

### Prometheus DOWN
```bash
curl http://localhost:8000/metrics
```

### Pas de logs dans Grafana
```bash
docker logs av_promtail
curl http://localhost:3100/ready
```

---

## 12. Évolutions possibles (reste à faire)

- Dashboard Grafana prêt à l’emploi
- Frontend web de chat
- Amélioration NLP (SBERT, FAISS)
- Support multilingue avancé
- Authentification utilisateur

---

## 13. Maintenance

Projet maintenu par l’équipe **Assistant Virtuel Campus**.
Se référer à ce README et aux dashboards Grafana pour le diagnostic.
