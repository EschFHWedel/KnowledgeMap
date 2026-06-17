"""
KnowledgeMap – API-Gateway
==========================

Einziger Eintrittspunkt des Systems. Nimmt alle Anfragen unter /api/v1
entgegen und leitet sie anhand der Ressource an den passenden Service
weiter:

    /api/v1/nodes, /api/v1/edges, /api/v1/graph   -> Graph-Service
    /api/v1/search, /api/v1/reindex               -> Search-Service

Die internen Endpoints der Services (z. B. /internal/index) sind über das
Gateway bewusst NICHT erreichbar – sie dienen nur der Kommunikation
zwischen den Services.

Interaktive API-Doku: http://localhost:8080/docs
"""

import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8081")
SEARCH_SERVICE_URL = os.getenv("SEARCH_SERVICE_URL", "http://localhost:8082")

# Welche Ressource wird von welchem Service bedient?
GRAPH_RESOURCES = {"nodes", "edges", "graph"}
SEARCH_RESOURCES = {"search", "reindex"}

app = FastAPI(
    title="KnowledgeMap – API-Gateway",
    version="0.1.0",
    description="Zentrale Eintrittstür: leitet Anfragen an die Services weiter.",
)


def target_for(full_path: str):
    """Bestimmt anhand der Ressource den Ziel-Service (oder None)."""
    resource = full_path.strip("/").split("/")[0] if full_path else ""
    if resource in GRAPH_RESOURCES:
        return GRAPH_SERVICE_URL
    if resource in SEARCH_RESOURCES:
        return SEARCH_SERVICE_URL
    return None


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "services": {
            "graph": GRAPH_SERVICE_URL,
            "search": SEARCH_SERVICE_URL,
        },
    }


@app.api_route(
    "/api/v1/{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["gateway"],
)
async def proxy(full_path: str, request: Request):
    base = target_for(full_path)
    if base is None:
        return JSONResponse(
            status_code=404,
            content={"code": "NO_ROUTE", "message": "Unbekannte Ressource."},
        )

    url = f"{base}/api/v1/{full_path}"
    body = await request.body()
    # Host- und Content-Length-Header nicht weiterreichen (setzt httpx selbst)
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    async with httpx.AsyncClient(timeout=30) as cx:
        upstream = await cx.request(
            request.method,
            url,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    # Hop-by-hop-Header herausfiltern
    excluded = {"content-encoding", "transfer-encoding", "connection", "content-length"}
    out_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in excluded
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=out_headers,
        media_type=upstream.headers.get("content-type"),
    )
