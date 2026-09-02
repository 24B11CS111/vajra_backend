import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./vajra_test.db")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("LLM_PROVIDER", "dummy")

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers


def test_application_imports():
    import main

    assert main.app.title == "VAJRA Backend"


def test_health_endpoint():
    import main

    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_generation():
    import main

    schema = main.app.openapi()

    assert schema["info"]["title"] == "VAJRA Backend"
    assert "/api/v1/me" in schema["paths"]
    assert "/api/v1/chat/conversations" in schema["paths"]
    assert "/api/v1/memory/" in schema["paths"]


def test_missing_authentication_is_rejected():
    import main

    client = TestClient(main.app)
    response = client.get("/api/v1/me")

    assert response.status_code in {401, 403}


def test_pydantic_memory_schema_validation():
    from app.schemas.memory import MemoryCreate, MemoryUpdate

    memory = MemoryCreate(
        content="User prefers concise answers.",
        memory_metadata={"source": "test"},
    )
    update = MemoryUpdate(memory_metadata={"source": "updated"})

    assert memory.metadata == {"source": "test"}
    assert update.metadata == {"source": "updated"}

    try:
        MemoryCreate(content="", importance=2.0)
    except ValidationError:
        pass
    else:
        raise AssertionError("importance outside 0..1 should fail validation")


def test_sqlalchemy_mappers_configure():
    import app.db.base  # noqa: F401

    configure_mappers()
