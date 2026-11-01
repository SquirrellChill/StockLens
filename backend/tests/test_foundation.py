from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.database import get_db


def test_foundation_health_check(client: TestClient):
    """Verifies the foundation GET /health endpoint matches user specification."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "StockLens API"
    }


def test_cors_headers_present(client: TestClient):
    """Verifies CORS headers are returned for allowed frontend origins."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_docs_and_openapi_endpoints(client: TestClient):
    """Verifies interactive OpenAPI documentation endpoints are available."""
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200

    openapi_res = client.get("/api/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert schema["info"]["title"] == "StockLens API"


def test_database_session_dependency(db_session: Session):
    """Verifies the database session management operates properly."""
    assert db_session.is_active
