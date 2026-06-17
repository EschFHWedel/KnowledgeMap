"""
Test-Client für den Graph-Service.

Spielt einen typischen Ablauf durch und prüft die Antworten:
  1. Knoten anlegen
  2. Knoten lesen
  3. Knoten ändern (mit korrekter Version)
  4. Änderung mit veralteter Version -> erwarteter 409-Konflikt
  5. Zweiten Knoten anlegen und beide verknüpfen
  6. Gesamten Graphen abrufen

Voraussetzung: Das System läuft (docker compose up) und der Graph-Service
ist unter http://localhost:8081 erreichbar.

Starten:
    pip install requests
    python test_client.py
"""

import sys
import requests

BASE = "http://localhost:8081/api/v1"


def check(bedingung: bool, beschreibung: str):
    status = "OK  " if bedingung else "FEHL"
    print(f"[{status}] {beschreibung}")
    if not bedingung:
        sys.exit(1)


def main():
    # 1. Knoten anlegen
    r = requests.post(BASE + "/nodes", json={
        "type": "concept",
        "title": "Eventual Consistency",
        "content": "Konsistenzmodell in verteilten Systemen.",
        "tags": ["verteilte-systeme"],
    })
    check(r.status_code == 201, "Knoten anlegen liefert 201")
    node = r.json()
    node_id = node["id"]
    check(node["version"] == 1, "neuer Knoten hat Version 1")

    # 2. Knoten lesen
    r = requests.get(f"{BASE}/nodes/{node_id}")
    check(r.status_code == 200, "Knoten lesen liefert 200")
    check(r.json()["title"] == "Eventual Consistency", "Titel stimmt")

    # 3. Knoten ändern (korrekte Version per If-Match)
    r = requests.put(f"{BASE}/nodes/{node_id}",
                     headers={"If-Match": "1"},
                     json={"type": "concept",
                           "title": "Eventual Consistency (überarbeitet)",
                           "content": "Aktualisierter Inhalt.",
                           "tags": ["verteilte-systeme", "konsistenz"]})
    check(r.status_code == 200, "Knoten ändern liefert 200")
    check(r.json()["version"] == 2, "Version wurde auf 2 erhöht")

    # 4. Änderung mit veralteter Version -> 409 Konflikt
    r = requests.put(f"{BASE}/nodes/{node_id}",
                     headers={"If-Match": "1"},
                     json={"type": "concept", "title": "Sollte scheitern",
                           "content": "", "tags": []})
    check(r.status_code == 409, "veraltete Version liefert 409 (Konflikt)")

    # 5. Zweiten Knoten anlegen und verknüpfen
    r = requests.post(BASE + "/nodes", json={
        "type": "definition", "title": "CAP-Theorem", "content": "", "tags": []})
    check(r.status_code == 201, "zweiten Knoten anlegen liefert 201")
    node2_id = r.json()["id"]

    r = requests.post(BASE + "/edges", json={
        "sourceId": node_id, "targetId": node2_id, "label": "verwandt mit"})
    check(r.status_code == 201, "Kante anlegen liefert 201")

    # 6. Graph abrufen
    r = requests.get(BASE + "/graph")
    check(r.status_code == 200, "Graph abrufen liefert 200")
    graph = r.json()
    check(len(graph["nodes"]) >= 2, "Graph enthält mindestens 2 Knoten")
    check(len(graph["edges"]) >= 1, "Graph enthält mindestens 1 Kante")

    print("\nAlle Tests erfolgreich durchlaufen.")


if __name__ == "__main__":
    main()
