# KnowledgeMap

Kollaboratives Wissensnetz – Microservice-System für die Veranstaltung
*Moderne Software Architekturen* (FH Wedel, SS 2026).

KnowledgeMap erlaubt es, Konzepte, Quellen, Notizen und deren Zusammenhänge als Graph
zu erfassen, kollaborativ zu bearbeiten und zu durchsuchen.

## Dokumentation

- Projektdokumentation: [`docs/dokumentation.md`](docs/dokumentation.md)
- Architektur & Diagramm: [`docs/architektur.md`](docs/architektur.md)
- API-Spezifikation Graph-Service: [`docs/api/graph-service.yaml`](docs/api/graph-service.yaml)
- Reflexion KI-Einsatz: [`docs/ki-einsatz.md`](docs/ki-einsatz.md)

## Komponenten

| Service | Aufgabe | Status |
|---|---|---|
| Frontend | Interaktive Graph-Oberfläche | umgesetzt |
| API-Gateway | Eintrittspunkt, Routing | umgesetzt |
| Graph-Service | CRUD Knoten & Kanten | umgesetzt |
| Search-Service | Volltextsuche | umgesetzt |
| Neo4j | Graph-Datenbank | eingebunden |
| Meilisearch | Suchindex | eingebunden |

## Schnellstart

Voraussetzung: Docker und Docker Compose.

```bash
docker compose up --build
```

Danach erreichbar:

| Dienst | Adresse |
|---|---|
| **Frontend** | http://localhost:3000 |
| API-Gateway | http://localhost:8080 |
| Graph-Service (API-Doku) | http://localhost:8081/docs |
| Search-Service (API-Doku) | http://localhost:8082/docs |
| Neo4j Browser | http://localhost:7474 (neo4j / knowledgemap) |
| Meilisearch | http://localhost:7700 |

## Tests

Bei laufendem System (zweites Terminal):

```bash
pip install requests
python services/graph-service/test_client.py
python services/search-service/test_client.py
python services/api-gateway/test_client.py
```

Die Tests laufen außerdem automatisch in der CI-Pipeline
(`.github/workflows/ci.yml`) bei jedem Push und Pull Request.

## Projektstruktur

```
knowledgemap/
├── docker-compose.yml          # Orchestrierung aller Komponenten
├── .github/workflows/ci.yml    # CI/CD-Pipeline
├── docs/                       # Architektur, API-Spec, Doku, KI-Reflexion
└── services/
    ├── frontend/               # Web-Oberfläche (nginx)
    ├── api-gateway/            # Reverse-Proxy / Eintrittspunkt
    ├── graph-service/          # CRUD Knoten & Kanten (Neo4j)
    └── search-service/         # Volltextsuche (Meilisearch)
```

## Entwicklung

Entwicklung in Feature-Branches, Integration über Pull Requests.

## Team

<!-- Namen ergänzen -->
