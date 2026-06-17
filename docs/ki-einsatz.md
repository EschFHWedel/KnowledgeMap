# Reflexion: KI-Einsatz im Entwicklungsprozess

> Teil der Projektdokumentation (siehe Aufgabenstellung, Punkt 4 & 6).
> Nach jeder relevanten Session kurz ergänzen – das spart am Ende viel Arbeit.

## Eingesetzte Werkzeuge

| Werkzeug | Wofür eingesetzt |
|---|---|
| Claude | Architekturentwurf, OpenAPI-Spec, Repo-Gerüst |
| <!-- z. B. GitHub Copilot --> | <!-- z. B. Code-Vervollständigung --> |
| <!-- z. B. v0.dev --> | <!-- z. B. Frontend-Generierung --> |

## Log

### 2026-__-__ – Architektur & API-Entwurf
- **Werkzeug:** Claude
- **Eingesetzt für:** Erstentwurf Architekturdiagramm (Mermaid) und OpenAPI-Spec des Graph-Service; Aufsetzen des Repo-Gerüsts.
- **Hilfreich:** Schneller, strukturierter Startpunkt; sinnvolle Defaults (zustandslose Services, optimistisches Locking, Eventual Consistency für Suche).
- **Grenzen / manuell angepasst:** <!-- z. B. NodeType-Enum im Team überarbeitet, ... -->

<!-- Weitere Einträge nach diesem Muster -->

### 2026-__-__ – Implementierung der Services
- **Werkzeug:** Claude
- **Eingesetzt für:** Grundgerüst und Implementierung von Graph-Service (FastAPI + Neo4j), Search-Service (Meilisearch), API-Gateway (Reverse-Proxy) und Frontend (vis-network); Test-Clients; docker-compose-Orchestrierung; GitHub-Actions-Pipeline; Projektdokumentation.
- **Hilfreich:** Schnelle, lauffähige Erstversionen ganzer Services inklusive Test-Clients; konsistenter Aufbau über alle Services hinweg; Erklärung der Schritte (Git, Docker, Authentifizierung) für die Inbetriebnahme.
- **Grenzen / manuell angepasst:** <!-- z. B. ein Endpoint las die Datenbank-Ergebnisse zunächst falsch aus (get_graph) und musste korrigiert werden; Node-Typen / Texte im Team final abgestimmt; ... -->

## Gesamteinschätzung

<!-- Am Projektende: Wo hat KI echten Mehrwert gebracht, wo war manuelle Arbeit/Review
     nötig, was würdet ihr beim nächsten Mal anders machen? -->
