# KnowledgeMap – Projektdokumentation

Microservice-System für das kollaborative Wissensnetz *KnowledgeMap*,
entstanden in der Veranstaltung *Moderne Software Architekturen* (FH Wedel,
Sommersemester 2026).

## 1. Überblick und MVP

KnowledgeMap erlaubt es, Konzepte, Quellen, Fragen, Definitionen und Notizen
als Knoten eines Graphen zu erfassen, sie zu verknüpfen, zu durchsuchen und
visuell zu navigieren. Das System ist als komponentenbasiertes
Microservice-System aufgebaut und lässt sich mit einem einzigen Kommando
starten.

Der Funktionsumfang orientiert sich am Gedanken des Minimal Viable Product.
Realisiert sind im MVP: das Anlegen, Lesen, Ändern und Löschen von Knoten,
das Verknüpfen von Knoten über benannte Kanten, das Abrufen des Graphen, eine
Volltextsuche sowie eine interaktive Web-Oberfläche. Bewusst noch nicht
umgesetzt und für eine spätere agile Erweiterung vorgesehen sind unter
anderem die Versionierung ganzer Wissensstände, eine feingranulare
Rechteverwaltung, der Export in Formate wie JSON-LD oder RDF sowie die
Plugin-Architektur für neue Knotentypen.

## 2. Architektur

Das System besteht aus vier selbst entwickelten Services und zwei
Standard-Komponenten. Das Architekturdiagramm und die zugrundeliegenden
Entscheidungen sind in [`architektur.md`](architektur.md) dokumentiert.

Alle selbst entwickelten Services sind **zustandslos** und damit horizontal
skalierbar. Der gesamte Zustand liegt ausschließlich in den beiden
zustandsbehafteten Datenhaltungs-Komponenten: dem Wissensgraphen in Neo4j und
dem Suchindex in Meilisearch.

| Komponente | Aufgabe | Technik | Zustand |
|---|---|---|---|
| Frontend | Interaktive Web-Oberfläche zur Graph-Navigation | HTML/JS + vis-network, ausgeliefert über nginx | zustandslos |
| API-Gateway | Einziger Eintrittspunkt, leitet Anfragen weiter | Python / FastAPI | zustandslos |
| Graph-Service | CRUD für Knoten und Kanten | Python / FastAPI | zustandslos |
| Search-Service | Volltextsuche und Indexpflege | Python / FastAPI | zustandslos |
| Neo4j | Persistenz des Wissensgraphen | Neo4j 5 | zustandsbehaftet |
| Meilisearch | Volltext-Suchindex | Meilisearch 1.7 | zustandsbehaftet |

### Konsistenz zwischen Graph und Suchindex

Der Suchindex wird **asynchron** aktualisiert: Legt der Graph-Service einen
Knoten an oder ändert ihn, meldet er die Änderung per HTTP an den
Search-Service, der den Knoten in Meilisearch aufnimmt. Diese Meldung erfolgt
nach dem Best-Effort-Prinzip – schlägt sie fehl oder ist der Search-Service
nicht erreichbar, läuft der Schreibvorgang im Graphen trotzdem erfolgreich
durch. Daraus folgt bewusst eine Eventual Consistency: Suchergebnisse können
dem aktuellen Stand des Graphen um kurze Zeit hinterherhinken. Der Vorteil ist
ein schneller, entkoppelter Schreibpfad. Über den Endpoint `POST /reindex`
lässt sich der Index jederzeit vollständig aus dem Graphen neu aufbauen.

Im MVP ist die Änderungsmeldung als direkter HTTP-Aufruf realisiert. Die
Schnittstelle ist so geschnitten, dass später eine Message Queue (etwa
RabbitMQ) dazwischengeschaltet werden kann, ohne die Services zu verändern.

### Behandlung konkurrierender Änderungen

Jeder Knoten trägt eine Versionsnummer. Eine Änderung muss die erwartete
Version über den `If-Match`-Header mitschicken. Stimmt sie nicht mit dem
aktuellen Stand überein, antwortet der Graph-Service mit `409 Conflict` und
liefert den aktuellen Stand zurück. Dieses optimistische Locking verhindert,
dass zwei gleichzeitige Bearbeitungen sich gegenseitig unbemerkt
überschreiben. Aufwändigere Verfahren wie CRDTs sind bewusst nicht Teil des
MVP.

## 3. Schnittstellen

Die Services kommunizieren über REST mit JSON (`application/json`). Jeder
Service stellt seine API automatisch als OpenAPI-Spezifikation bereit und
bietet unter `/docs` eine interaktive Swagger-Oberfläche zum Ausprobieren.

Die fachlich vollständige Schnittstellendefinition des Graph-Service liegt
zusätzlich als handgepflegte Spezifikation in
[`api/graph-service.yaml`](api/graph-service.yaml).

Wichtigste Endpoints (jeweils unter `/api/v1`):

| Methode | Pfad | Service | Zweck |
|---|---|---|---|
| POST | `/nodes` | Graph | Knoten anlegen |
| GET | `/nodes/{id}` | Graph | Knoten lesen |
| PUT | `/nodes/{id}` | Graph | Knoten ändern (mit `If-Match`) |
| DELETE | `/nodes/{id}` | Graph | Knoten löschen |
| POST | `/edges` | Graph | Knoten verknüpfen |
| DELETE | `/edges/{id}` | Graph | Kante löschen |
| GET | `/graph` | Graph | (Teil-)Graphen abrufen |
| GET | `/search?q=` | Search | Volltextsuche |
| POST | `/reindex` | Search | Suchindex neu aufbauen |

Das API-Gateway arbeitet als generischer Reverse-Proxy: Es nimmt alle
Anfragen unter `/api/v1` entgegen und leitet sie anhand der Ressource an den
zuständigen Service weiter. Die internen Endpoints der Services (etwa
`/internal/index`) sind über das Gateway absichtlich nicht erreichbar.

## 4. Orchestrierung und Deployment

Das gesamte System wird über Docker Compose orchestriert und lässt sich nach
dem Auschecken des Repositories mit einem einzigen Kommando starten:

```bash
docker compose up --build
```

Damit werden alle sechs Container gebaut und gestartet. Die Services warten
beim Start aktiv darauf, dass ihre Datenbank erreichbar ist, sodass die
Startreihenfolge unkritisch ist.

| Dienst | Adresse | Zweck |
|---|---|---|
| Frontend | http://localhost:3000 | Web-Oberfläche |
| API-Gateway | http://localhost:8080 | Eintrittspunkt der API |
| Graph-Service | http://localhost:8081/docs | API-Doku Graph |
| Search-Service | http://localhost:8082/docs | API-Doku Suche |
| Neo4j Browser | http://localhost:7474 | Datenbank-Oberfläche |
| Meilisearch | http://localhost:7700 | Suchindex |

Für ein Deployment auf einem Internet-Server wird das Repository auf den
Server geklont und dort dasselbe Kommando ausgeführt. Drei Punkte sind dabei
anzupassen: Die im Frontend hinterlegte API-Adresse (`localhost:8080`) muss
auf die öffentliche Server-Adresse zeigen; die CORS-Einstellung im Gateway
sollte von „alle Quellen erlaubt" auf die konkrete Frontend-Domain
eingeschränkt werden; und die Zugangsdaten für Neo4j und Meilisearch sollten
über Umgebungsvariablen statt fest im Compose-File gesetzt werden.

## 5. Tests

Zu jedem Service gehört ein Test-Client (`services/*/test_client.py`), der die
jeweilige API über verschiedene Abläufe anspricht und die Antworten prüft –
darunter das Anlegen, Lesen und Ändern von Knoten, der erwartete
Versionskonflikt, das Zusammenspiel von Graph- und Search-Service über die
Änderungskette sowie die Weiterleitung durch das Gateway.

Diese Tests laufen zusätzlich automatisch in einer CI/CD-Pipeline mit GitHub
Actions (`.github/workflows/ci.yml`): Bei jedem Push und jedem Pull Request
wird das vollständige System gebaut, gestartet und mit allen drei
Test-Clients geprüft. Schlägt ein Test fehl, schlägt der Build fehl.

## 6. Reflexion des KI-Einsatzes

Die laufende Reflexion des KI-Einsatzes wird in
[`ki-einsatz.md`](ki-einsatz.md) geführt und ist Teil dieser Dokumentation.

## 7. Ausblick

Über das MVP hinaus sind als nächste Schritte vorgesehen: die Versionierung
ganzer Wissensstände, eine Rechteverwaltung auf Graph- und Knotenebene
(sinnvoll im Gateway angesiedelt), der Export in Markdown, JSON-LD und RDF,
die Plugin-Architektur für neue Knotentypen wie Formeln oder Code-Snippets
sowie die Entkopplung der Änderungs-Events über eine Message Queue.
