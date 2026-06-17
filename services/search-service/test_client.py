"""
Test-Client für den Search-Service.

Prüft das Zusammenspiel von Graph-Service und Search-Service:
  1. Knoten im Graph-Service anlegen (löst automatisch ein Index-Event aus)
  2. Warten, bis der Knoten im Suchindex auftaucht (Eventual Consistency)
  3. Reindex über alle vorhandenen Knoten anstoßen

Voraussetzung: Das Gesamtsystem läuft (docker compose up --build) und
beide Services sind erreichbar:
  - Graph-Service:  http://localhost:8081
  - Search-Service: http://localhost:8082

Starten:
    python test_client.py
"""

import sys
import time
import uuid

import requests

GRAPH = "http://localhost:8081/api/v1"
SEARCH = "http://localhost:8082/api/v1"


def check(bedingung: bool, beschreibung: str):
    status = "OK  " if bedingung else "FEHL"
    print(f"[{status}] {beschreibung}")
    if not bedingung:
        sys.exit(1)


def main():
    # Eindeutiger Begriff, damit der Test wiederholbar ist
    marker = "Suchtest-" + uuid.uuid4().hex[:8]

    # 1. Knoten im Graph-Service anlegen
    r = requests.post(GRAPH + "/nodes", json={
        "type": "concept",
        "title": marker,
        "content": "Inhalt fuer die Volltextsuche.",
        "tags": ["suche"],
    })
    check(r.status_code == 201, "Knoten im Graph-Service anlegen liefert 201")

    # 2. Auf den Suchindex warten (asynchrone Aktualisierung)
    found = False
    for _ in range(15):  # bis zu 15 Sekunden
        res = requests.get(SEARCH + "/search", params={"q": marker})
        if res.status_code == 200 and any(
            h.get("title") == marker for h in res.json().get("hits", [])
        ):
            found = True
            break
        time.sleep(1)
    check(found, "angelegter Knoten taucht in der Suche auf (Event-Kette)")

    # 3. Reindex anstoßen
    r = requests.post(SEARCH + "/reindex")
    check(r.status_code == 200, "Reindex liefert 200")
    check(r.json()["reindexed"] >= 1, "Reindex hat mindestens 1 Knoten erfasst")

    print("\nAlle Tests erfolgreich durchlaufen.")


if __name__ == "__main__":
    main()
