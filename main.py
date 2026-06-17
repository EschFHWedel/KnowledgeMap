"""
KnowledgeMap – Graph-Service
============================

Microservice für CRUD von Knoten und Kanten des Wissensgraphen.
Persistenz in Neo4j. Konkurrierende Änderungen werden über optimistisches
Locking (Versionsnummer + If-Match-Header) behandelt.

Die interaktive API-Doku (Swagger UI) ist nach dem Start unter
http://localhost:8081/docs erreichbar – dort kannst du alle Endpoints
direkt im Browser ausprobieren, ohne extra Werkzeug.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, Path, Query
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Konfiguration (kommt aus Umgebungsvariablen, siehe docker-compose.yml)
# ---------------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "knowledgemap")

# Globaler Treiber (wird beim Start gesetzt)
driver = None


def now_iso() -> str:
    """Aktueller Zeitstempel im ISO-8601-Format (UTC)."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Lifespan: Verbindung zu Neo4j beim Start aufbauen (mit Wiederholungen,
# falls die Datenbank noch hochfährt) und beim Beenden sauber schließen.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global driver
    last_error = None
    for attempt in range(1, 31):  # bis zu ~30 Sekunden warten
        try:
            driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            driver.verify_connectivity()
            print(f"[graph-service] Mit Neo4j verbunden ({NEO4J_URI}).")
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[graph-service] Warte auf Neo4j... (Versuch {attempt})")
            time.sleep(1)
    else:
        raise RuntimeError(f"Keine Verbindung zu Neo4j: {last_error}")

    yield  # ab hier läuft die Anwendung

    if driver is not None:
        driver.close()


app = FastAPI(
    title="KnowledgeMap – Graph-Service",
    version="0.1.0",
    description="CRUD für Knoten und Kanten des Wissensgraphen.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Datenmodelle (entsprechen den Schemas aus docs/api/graph-service.yaml)
# ---------------------------------------------------------------------------
NODE_TYPES = ["concept", "source", "question", "definition", "note"]


class NodeCreate(BaseModel):
    type: str = Field(..., examples=["concept"])
    title: str = Field(..., max_length=200, examples=["Eventual Consistency"])
    content: str = Field("", examples=["Konsistenzmodell, bei dem ..."])
    tags: list[str] = Field(default_factory=list)


class EdgeCreate(BaseModel):
    sourceId: str
    targetId: str
    label: str = Field(..., examples=["erklärt"])


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Neo4j-Records in JSON-freundliche dicts umwandeln
# ---------------------------------------------------------------------------
def node_to_dict(record_node) -> dict:
    n = dict(record_node)
    return {
        "id": n["id"],
        "type": n["type"],
        "title": n["title"],
        "content": n.get("content", ""),
        "tags": n.get("tags", []),
        "version": n["version"],
        "createdAt": n["createdAt"],
        "updatedAt": n["updatedAt"],
    }


def error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


# ---------------------------------------------------------------------------
# Endpoints – Knoten
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
def health():
    """Einfacher Gesundheitscheck."""
    return {"status": "ok"}


@app.post("/api/v1/nodes", status_code=201, tags=["nodes"])
def create_node(node: NodeCreate):
    if node.type not in NODE_TYPES:
        return error("INVALID_TYPE", f"type muss einer von {NODE_TYPES} sein.", 400)

    new_id = str(uuid.uuid4())
    ts = now_iso()
    query = """
        CREATE (n:Node {
            id: $id, type: $type, title: $title, content: $content,
            tags: $tags, version: 1, createdAt: $ts, updatedAt: $ts
        })
        RETURN n
    """
    with driver.session() as session:
        rec = session.run(
            query, id=new_id, type=node.type, title=node.title,
            content=node.content, tags=node.tags, ts=ts,
        ).single()
    return node_to_dict(rec["n"])


@app.get("/api/v1/nodes/{node_id}", tags=["nodes"])
def get_node(node_id: str = Path(...)):
    with driver.session() as session:
        rec = session.run(
            "MATCH (n:Node {id: $id}) RETURN n", id=node_id
        ).single()
    if rec is None:
        return error("NOT_FOUND", "Knoten nicht gefunden.", 404)
    return node_to_dict(rec["n"])


@app.put("/api/v1/nodes/{node_id}", tags=["nodes"])
def update_node(
    node: NodeCreate,
    node_id: str = Path(...),
    if_match: int = Header(..., alias="If-Match"),
):
    if node.type not in NODE_TYPES:
        return error("INVALID_TYPE", f"type muss einer von {NODE_TYPES} sein.", 400)

    with driver.session() as session:
        current = session.run(
            "MATCH (n:Node {id: $id}) RETURN n", id=node_id
        ).single()
        if current is None:
            return error("NOT_FOUND", "Knoten nicht gefunden.", 404)

        current_version = current["n"]["version"]
        if current_version != if_match:
            # Versionskonflikt: aktuellen Stand zurückgeben (409)
            return JSONResponse(
                status_code=409,
                content=node_to_dict(current["n"]),
            )

        ts = now_iso()
        rec = session.run(
            """
            MATCH (n:Node {id: $id})
            SET n.type = $type, n.title = $title, n.content = $content,
                n.tags = $tags, n.version = n.version + 1, n.updatedAt = $ts
            RETURN n
            """,
            id=node_id, type=node.type, title=node.title,
            content=node.content, tags=node.tags, ts=ts,
        ).single()
    return node_to_dict(rec["n"])


@app.delete("/api/v1/nodes/{node_id}", status_code=204, tags=["nodes"])
def delete_node(node_id: str = Path(...)):
    with driver.session() as session:
        exists = session.run(
            "MATCH (n:Node {id: $id}) RETURN n", id=node_id
        ).single()
        if exists is None:
            return error("NOT_FOUND", "Knoten nicht gefunden.", 404)
        # DETACH DELETE entfernt den Knoten samt anhängender Kanten
        session.run("MATCH (n:Node {id: $id}) DETACH DELETE n", id=node_id)
    return JSONResponse(status_code=204, content=None)


# ---------------------------------------------------------------------------
# Endpoints – Kanten
# ---------------------------------------------------------------------------
@app.post("/api/v1/edges", status_code=201, tags=["edges"])
def create_edge(edge: EdgeCreate):
    new_id = str(uuid.uuid4())
    ts = now_iso()
    query = """
        MATCH (a:Node {id: $source}), (b:Node {id: $target})
        CREATE (a)-[r:LINK {id: $id, label: $label, createdAt: $ts}]->(b)
        RETURN r, a.id AS source, b.id AS target
    """
    with driver.session() as session:
        rec = session.run(
            query, source=edge.sourceId, target=edge.targetId,
            label=edge.label, id=new_id, ts=ts,
        ).single()
    if rec is None:
        return error("NOT_FOUND", "Quell- oder Zielknoten existiert nicht.", 404)
    return {
        "id": new_id,
        "sourceId": rec["source"],
        "targetId": rec["target"],
        "label": edge.label,
        "createdAt": ts,
    }


@app.delete("/api/v1/edges/{edge_id}", status_code=204, tags=["edges"])
def delete_edge(edge_id: str = Path(...)):
    with driver.session() as session:
        rec = session.run(
            "MATCH ()-[r:LINK {id: $id}]->() DELETE r RETURN count(r) AS c",
            id=edge_id,
        ).single()
    if rec["c"] == 0:
        return error("NOT_FOUND", "Kante nicht gefunden.", 404)
    return JSONResponse(status_code=204, content=None)


# ---------------------------------------------------------------------------
# Endpoint – Graph abrufen
# ---------------------------------------------------------------------------
@app.get("/api/v1/graph", tags=["graph"])
def get_graph(
    rootId: Optional[str] = Query(None),
    depth: int = Query(2, ge=1, le=5),
):
    with driver.session() as session:
        if rootId is None:
            # Gesamten Graphen zurückgeben (MVP)
            node_recs = session.run("MATCH (n:Node) RETURN n").data()
            edge_recs = session.run(
                """
                MATCH (a:Node)-[r:LINK]->(b:Node)
                RETURN r, a.id AS source, b.id AS target
                """
            ).data()
        else:
            root = session.run(
                "MATCH (n:Node {id: $id}) RETURN n", id=rootId
            ).single()
            if root is None:
                return error("NOT_FOUND", "Startknoten nicht gefunden.", 404)

            # Knoten im Umkreis von <depth> Schritten (ungerichtet) einsammeln.
            # depth ist durch Query-Validierung auf 1..5 begrenzt -> sicher.
            node_recs = session.run(
                f"MATCH (root:Node {{id: $id}})-[:LINK*0..{depth}]-(n:Node) "
                f"RETURN DISTINCT n",
                id=rootId,
            ).data()
            ids = [node_to_dict(r["n"])["id"] for r in node_recs]
            edge_recs = session.run(
                """
                MATCH (a:Node)-[r:LINK]->(b:Node)
                WHERE a.id IN $ids AND b.id IN $ids
                RETURN r, a.id AS source, b.id AS target
                """,
                ids=ids,
            ).data()

    nodes = [node_to_dict(r["n"]) for r in node_recs]
    edges = [
        {
            "id": r["r"]["id"],
            "sourceId": r["source"],
            "targetId": r["target"],
            "label": r["r"]["label"],
            "createdAt": r["r"]["createdAt"],
        }
        for r in edge_recs
    ]
    return {"nodes": nodes, "edges": edges}
