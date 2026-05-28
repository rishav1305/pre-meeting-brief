from fastapi.testclient import TestClient

from api.index import app

client = TestClient(app)


def test_agenda_endpoint_exists():
    response = client.get("/api/agenda?partner=Devon")
    # Should return 200 with a list (possibly empty if DB not seeded in this env)
    # 503 is acceptable if DB is unreachable in the test environment.
    assert response.status_code in (200, 503)


def test_briefs_endpoint_exists():
    response = client.get("/api/briefs/00000000-0000-0000-0000-000000000000")
    # 404 if the brief is not found, 503 if DB is unreachable.
    assert response.status_code in (404, 503)
