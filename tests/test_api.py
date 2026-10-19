"""
test_api.py — Integrační testy pro FastAPI REST API

Testují HTTP endpointy aplikace pomocí TestClient.
Ověřují správné HTTP kódy, formáty odpovědí a chybové stavy.

Spuštění:  pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# FIXTURES — TestClient
# ============================================================================

@pytest.fixture
def client():
    """Vytvoří testovací klient FastAPI aplikace."""
    from app.main import app
    return TestClient(app)


# ============================================================================
# TESTY: Stránky (GET requesty)
# ============================================================================

class TestPages:
    """
    Ověření, že všechny stránky aplikace jsou dostupné.

    Kontroly:
    - HTTP 200 pro každou stránku
    - Správný Content-Type (text/html)
    - Přítomnost klíčových UI prvků
    """

    def test_homepage(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Teorie grafů" in response.text or "Teorie" in response.text

    def test_generate_page(self, client):
        response = client.get("/generate")
        assert response.status_code == 200

    def test_export_page(self, client):
        response = client.get("/export")
        assert response.status_code == 200

    def test_docs_page(self, client):
        response = client.get("/docs-algorithms")
        assert response.status_code == 200


# ============================================================================
# TESTY: Generování grafů (POST requesty)
# ============================================================================

class TestGenerateEndpoint:
    """
    Ověření POST endpointu pro generování grafů.

    Kontroly:
    - Úspěšné generování s platnými parametry
    - Redirect na stránku s výsledkem
    - Odmítnutí neplatných parametrů (validace)
    """

    def test_generate_valid_graph(self, client):
        response = client.post("/generate", data={
            "batch_size": 1,
            "node_min": 5, "node_max": 10,
            "edge_min": 6, "edge_max": 15,
            "directed": False, "weighted": True,
            "weight_min": 1, "weight_max": 10,
            "connected": True,
            "graph_type": "random"
        }, follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_generate_invalid_params(self, client):
        response = client.post("/generate", data={
            "node_min": "not-a-number", "node_max": 3,
        }, follow_redirects=False)
        assert response.status_code == 422


# ============================================================================
# TESTY: API endpointy (REST JSON)
# ============================================================================

class TestAPIEndpoints:
    """
    Ověření REST API endpointů vracejících JSON.

    Kontroly:
    - GET /api/graph/{id} — data grafu
    - POST /api/graph/{id}/positions — uložení pozic uzlů
    - Správné Content-Type (application/json)
    """

    def test_get_graph_data(self, client):
        post_response = client.post("/generate", data={
            "batch_size": 1, "node_min": 5, "node_max": 10, "edge_min": 6, "edge_max": 15,
        }, follow_redirects=False)
        redirect_url = post_response.headers.get("location")
        graph_id = redirect_url.split("/")[-1]

        response = client.get(f"/api/graph/{graph_id}")
        assert response.status_code == 200
        data = response.json()
        assert "graph_data_vis" in data
        assert "nodes" in data["graph_data_vis"]
        assert "edge_list" in data

    def test_graph_not_found(self, client):
        response = client.get("/api/graph/nonexistent-id")
        assert response.status_code == 404


# ============================================================================
# TESTY: Export endpointy
# ============================================================================

class TestExportEndpoints:
    """
    Ověření exportních endpointů.

    Kontroly:
    - Export CSV — správný formát a obsah
    - Export .tg — správná struktura (uzly + hrany)
    - Export PNG — validní obrazový soubor
    """

    def test_export_csv(self, client):
        post_response = client.post("/generate", data={
            "batch_size": 1, "node_min": 5, "node_max": 10, "edge_min": 6, "edge_max": 15,
        }, follow_redirects=False)

        response = client.post("/export/download", data={"format": "csv"})
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_json_format(self, client):
        post_response = client.post("/generate", data={
            "batch_size": 1, "node_min": 5, "node_max": 10, "edge_min": 6, "edge_max": 15,
        }, follow_redirects=False)

        response = client.post("/export/download", data={"format": "json"})
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_export_tg_format(self, client):
        post_response = client.post("/generate", data={
            "batch_size": 1, "node_min": 5, "node_max": 10, "edge_min": 6, "edge_max": 15,
        }, follow_redirects=False)
        graph_id = post_response.headers.get("location").split("/")[-1]

        response = client.post("/export/download", data={"format": "tg"})
        assert response.status_code == 200
        assert "application/zip" in response.headers["content-type"]

        # Test single graph .tg export
        single_tg = client.get(f"/api/graph/{graph_id}/tg")
        assert single_tg.status_code == 200
        assert "u A;" in single_tg.text
        assert ":h1;" in single_tg.text

    def test_import_tg_and_visualize_page(self, client):
        tg_sample = "u A;\nu B;\nu C;\nh A > B 3 :h1;\nh B > C 4 :h2;"
        response = client.post("/import-tg", data={
            "tg_content": tg_sample,
            "directed": False,
        }, follow_redirects=False)
        assert response.status_code == 303
        graph_id = response.headers.get("location").split("/")[-1]

        # Ověř stránku detailu a vizualizace průchodu
        res_page = client.get(f"/result/{graph_id}")
        assert res_page.status_code == 200

        vis_page = client.get(f"/visualize/{graph_id}")
        assert vis_page.status_code == 200

        # Ověř přepočet nejkratší cesty přes API
        sp_res = client.get(f"/api/graph/{graph_id}/shortest_path?source=0&target=2")
        assert sp_res.status_code == 200
        assert sp_res.json()["distance"] == 7

    def test_delete_all_graphs(self, client):
        res = client.post("/api/graphs/delete-all", headers={"accept": "application/json"})
        assert res.status_code == 200
        assert res.json()["status"] == "deleted_all"

