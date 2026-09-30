"""Pruebas unitarias e integrales para la persistencia de simulaciones en DuckDB (Hito 10)."""

import pytest
from fastapi.testclient import TestClient

from src.data.market_store import MarketDataStore
from src.scrapers.market_service import MarketDataService
from src.app.api import app, get_market_service


@pytest.fixture
def memory_store():
    store = MarketDataStore(db_path=":memory:")
    yield store
    store.close()


@pytest.fixture
def memory_service(memory_store):
    return MarketDataService(store=memory_store)


@pytest.fixture
def client(memory_service):
    app.dependency_overrides[get_market_service] = lambda: memory_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_market_store_save_and_retrieve(memory_store):
    """Verifica que MarketDataStore guarde y recupere simulaciones en DuckDB."""
    sim_data = {
        "title": "Evaluación Banco Santander",
        "client_name": "Juan Pérez",
        "current_bank": "Banco de Chile",
        "balance_uf": 3200.0,
        "annual_rate_pct": 5.20,
        "months_remaining": 180,
        "current_dividend_uf": 23.10,
        "fire_insurance_uf": 0.70,
        "target_bank": "Santander",
        "target_rate_pct": 4.15,
        "target_term_years": 15,
        "npv_uf": 128.50,
        "monthly_savings_uf": 2.15,
        "payback_months": 22,
        "recommendation_flag": "RECOMENDADO",
        "metadata_json": {"operation_number": "12345678", "uf_value": 40942.74},
    }

    sim_id = memory_store.save_simulation(sim_data)
    assert sim_id is not None
    assert sim_id.startswith("sim-")

    # Recuperar por ID
    retrieved = memory_store.get_saved_simulation_by_id(sim_id)
    assert retrieved is not None
    assert retrieved["id"] == sim_id
    assert retrieved["title"] == "Evaluación Banco Santander"
    assert retrieved["client_name"] == "Juan Pérez"
    assert retrieved["balance_uf"] == 3200.0
    assert retrieved["npv_uf"] == 128.50
    assert retrieved["payback_months"] == 22
    assert retrieved["metadata_json"]["operation_number"] == "12345678"

    # Listar simulaciones
    all_sims = memory_store.get_saved_simulations()
    assert len(all_sims) == 1
    assert all_sims[0]["id"] == sim_id

    # Eliminar simulación
    deleted = memory_store.delete_saved_simulation(sim_id)
    assert deleted is True

    # Verificar que ya no existe
    assert memory_store.get_saved_simulation_by_id(sim_id) is None
    assert len(memory_store.get_saved_simulations()) == 0


def test_api_simulations_crud(client):
    """Prueba el ciclo de vida CRUD completo de simulaciones vía API REST."""
    payload = {
        "title": "Simulación BCI 20 años",
        "client_name": "María González",
        "current_bank": "BancoEstado",
        "balance_uf": 2800.0,
        "annual_rate_pct": 5.40,
        "months_remaining": 240,
        "current_dividend_uf": 18.50,
        "fire_insurance_uf": 0.60,
        "target_bank": "BCI",
        "target_rate_pct": 4.30,
        "target_term_years": 20,
        "npv_uf": 95.30,
        "monthly_savings_uf": 1.80,
        "payback_months": 28,
        "recommendation_flag": "RECOMENDADO",
        "metadata_json": {"notes": "Evaluación con financiamiento de gastos"},
    }

    # 1. Guardar
    resp_post = client.post("/api/v1/simulations/save", json=payload)
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["status"] == "SUCCESS"
    sim_id = data_post["id"]

    # 2. Listar
    resp_list = client.get("/api/v1/simulations")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert data_list["count"] >= 1
    assert any(s["id"] == sim_id for s in data_list["simulations"])

    # 3. Obtener detalle
    resp_detail = client.get(f"/api/v1/simulations/{sim_id}")
    assert resp_detail.status_code == 200
    data_detail = resp_detail.json()
    assert data_detail["id"] == sim_id
    assert data_detail["client_name"] == "María González"
    assert data_detail["balance_uf"] == 2800.0

    # 4. Eliminar
    resp_del = client.delete(f"/api/v1/simulations/{sim_id}")
    assert resp_del.status_code == 200
    assert resp_del.json()["status"] == "SUCCESS"

    # 5. Verificar 404 al intentar obtener de nuevo
    resp_not_found = client.get(f"/api/v1/simulations/{sim_id}")
    assert resp_not_found.status_code == 404


def test_api_delete_non_existent(client):
    """Comprueba el manejo de error 404 al eliminar un ID que no existe."""
    resp = client.delete("/api/v1/simulations/non-existent-id")
    assert resp.status_code == 404
