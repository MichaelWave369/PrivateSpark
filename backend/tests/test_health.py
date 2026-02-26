from fastapi.testclient import TestClient

from privatespark.main import app


client = TestClient(app)


def test_healthz_ok():
    res = client.get('/api/healthz')
    assert res.status_code == 200
    body = res.json()
    assert body['ok'] is True
    assert 'version' in body


def test_models_safe_without_ollama():
    res = client.get('/api/models')
    assert res.status_code == 200
    body = res.json()
    assert 'models' in body
    assert isinstance(body['models'], list)
