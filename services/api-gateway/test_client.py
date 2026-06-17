"""
Test-Client für das API-Gateway.

Prüft, dass alle Anfragen über den einen Gateway-Port (8080) laufen und
korrekt an Graph- und Search-Service weitergeleitet werden:
  1. Knoten über das Gateway anlegen   (-> Graph-Service)
  2. Graphen über das Gateway abrufen   (-> Graph-Service)
  3. Über das Gateway suchen            (-> Search-Service)

Voraussetzung: Gesamtsystem läuft (docker compose up --build),
Gateway erreichbar unter http://localhost:8080.

Starten:
    python test_client.py
"""

import sys
import time
import uuid

import requests

GW = "http://localhost:8080/api/v1"


def check(bedingung: bool, beschreibung: str):
    status = "OK  " if bedingung else "FEHL"
    print(f"[{status}] {beschreibung}")
    if not bedingung:
        sys.exit(1)


def main():
    marker = "Gateway-Test-" + uuid.uuid4().hex[:8]

    # 1. Knoten über das Gateway anlegen (Weiterleitung an Graph-Service)
    r = requests.post(GW + "/nodes", json={
        "type": "concept", "title": marker, "content": "Test", "tags": []})
    check(r.status_code == 201, "Knoten anlegen ueber Gateway liefert 201")

    # 2. Graphen über das Gateway abrufen
    r = requests.get(GW + "/graph")
    check(r.status_code == 200, "Graph abrufen ueber Gateway liefert 200")
    check(any(n["title"] == marker for n in r.json()["nodes"]),
          "angelegter Knoten ist im Graphen enthalten")

    # 3. Über das Gateway suchen (Weiterleitung an Search-Service)
    found = False
    for _ in range(15):
        r = requests.get(GW + "/search", params={"q": marker})
        if r.status_code == 200 and any(
            h.get("title") == marker for h in r.json().get("hits", [])
        ):
            found = True
            break
        time.sleep(1)
    check(found, "Suche ueber Gateway findet den Knoten")

    print("\nAlle Tests erfolgreich durchlaufen.")


if __name__ == "__main__":
    main()
