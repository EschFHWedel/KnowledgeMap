# KnowledgeMap

Kollaboratives Wissensnetz – Microservice-System für die Veranstaltung
*Moderne Software Architekturen* (FH Wedel, SS 2026).

KnowledgeMap erlaubt es, Konzepte, Quellen, Notizen und deren Zusammenhänge als Graph
zu erfassen, kollaborativ zu bearbeiten und zu durchsuchen.

## Architektur

Komponentenbasiertes Microservice-System. Alle Services sind zustandslos und horizontal
skalierbar; Zustand liegt ausschließlich in Neo4j (Graph) und Meilisearch (Suchindex).

Details und Diagramm: [`docs/architektur.md`](docs/architektur.md)
API-Spezifikation Graph-Service: [`docs/api/graph-service.yaml`](docs/api/graph-service.yaml)

## Komponenten

| Service | Aufgabe | Status |
|---|---|---|
| API-Gateway | Eintrittspunkt, Routing | geplant |
| Graph-Service | CRUD Knoten & Kanten | in Arbeit |
| Search-Service | Volltextsuche | geplant |
| Collab-Service | Versionierung, Konflikte | geplant |
| Neo4j | Graph-Datenbank | eingebunden |
| Meilisearch | Suchindex | eingebunden |

## Schnellstart

Voraussetzung: Docker und Docker Compose.

```bash
docker compose up
```

Damit starten aktuell die Standard-Komponenten:

- **Neo4j Browser:** http://localhost:7474 (Login: `neo4j` / `knowledgemap`)
- **Meilisearch:** http://localhost:7700

Die eigenen Services (graph-service etc.) werden ergänzt, sobald implementiert –
sie sind in der `docker-compose.yml` bereits vorbereitet und auskommentiert.

## Projektstruktur

```
knowledgemap/
├── docker-compose.yml      # Orchestrierung aller Komponenten
├── docs/
│   ├── architektur.md      # Architekturdiagramm & Entscheidungen
│   ├── api/
│   │   └── graph-service.yaml   # OpenAPI-Spec Graph-Service
│   └── ki-einsatz.md       # Reflexion KI-Einsatz (Teil der Bewertung!)
└── services/
    └── graph-service/      # Implementierung Graph-Service
```

## Entwicklung

Entwicklung in Feature-Branches, Integration über Pull Requests.

## Team

<!-- Namen ergänzen -->
