"""
KnowledgeMap – Search-Service
=============================

Microservice für die Volltextsuche. Hält einen Suchindex in Meilisearch
aktuell und beantwortet Suchanfragen.

Der Index wird über interne Endpoints aktualisiert, die der Graph-Service
bei jeder Änderung aufruft (Änderungs-Events). Dadurch ist der Suchindex
vom Schreibpfad des Graphen entkoppelt (Eventual Consistency): Treffer
können wenige Augenblicke hinter dem aktuellen Stand liegen.

Interaktive API-Doku nach dem Start: http://localhost:8082/docs
"""

import os
import time
from contextlib import asynccontextmanager

import meilisearch
import requests
from fastapi import FastAPI, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
MEILI_URL = os.getenv("MEILI_URL", "http://localhost:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "knowledgemap-dev-key")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8081")
INDEX_NAME = "nodes"

client = None
index = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, index
    last_error = None
    for attempt in range(1, 31):
        try:
            client = meilisearch.Client(MEILI_URL, MEILI_KEY)
            client.health()  # wirft, falls Meilisearch noch nicht bereit ist
            # Index anlegen (idempotent) und durchsuchbare Felder festlegen
            try:
                client.create_index(INDEX_NAME, {"primaryKey": "id"})
            except Exception:  # noqa: BLE001  – existiert bereits
                pass
            index = client.index(INDEX_NAME)
            index.update_searchable_attributes(["title", "content", "tags", "type"])
            print(f"[search-service] Mit Meilisearch verbunden ({MEILI_URL}).")
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[search-service] Warte auf Meilisearch... (Versuch {attempt})")
            time.sleep(1)
    else:
        raise RuntimeError(f"Keine Verbindung zu Meilisearch: {last_error}")

    yield


app = FastAPI(
    title="KnowledgeMap – Search-Service",
    version="0.1.0",
    description="Volltextsuche über die Knoten des Wissensgraphen.",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Datenmodell für den indexierten Knoten
# ---------------------------------------------------------------------------
class NodeDoc(BaseModel):
    id: str
    type: str = ""
    title: str = ""
    content: str = ""
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Öffentliche Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/api/v1/search", tags=["search"])
def search(q: str = Query(..., min_length=1, description="Suchbegriff")):
    """Volltextsuche über Titel, Inhalt, Tags und Typ der Knoten."""
    result = index.search(q)
    return {"query": q, "hits": result.get("hits", [])}


@app.post("/api/v1/reindex", tags=["search"])
def reindex():
    """
    Holt alle Knoten vom Graph-Service und indexiert sie neu.
    Nützlich, um den Index nach einem Neustart oder für bereits vor dem
    Start des Search-Service angelegte Knoten aufzubauen.
    """
    resp = requests.get(f"{GRAPH_SERVICE_URL}/api/v1/graph", timeout=10)
    resp.raise_for_status()
    nodes = resp.json().get("nodes", [])
    docs = [
        {
            "id": n["id"],
            "type": n.get("type", ""),
            "title": n.get("title", ""),
            "content": n.get("content", ""),
            "tags": n.get("tags", []),
        }
        for n in nodes
    ]
    if docs:
        index.add_documents(docs, primary_key="id")
    return {"reindexed": len(docs)}


# ---------------------------------------------------------------------------
# Interne Endpoints – werden vom Graph-Service aufgerufen (Änderungs-Events)
# ---------------------------------------------------------------------------
@app.put("/internal/index", tags=["internal"])
def upsert_document(doc: NodeDoc):
    """Knoten in den Suchindex aufnehmen oder aktualisieren."""
    index.add_documents([doc.model_dump()], primary_key="id")
    return {"status": "queued"}


@app.delete("/internal/index/{node_id}", status_code=204, tags=["internal"])
def remove_document(node_id: str = Path(...)):
    """Knoten aus dem Suchindex entfernen."""
    index.delete_document(node_id)
    return JSONResponse(status_code=204, content=None)
