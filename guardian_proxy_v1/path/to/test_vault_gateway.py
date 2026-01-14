from fastapi.testclient import TestClient
from path.to.vault_gateway import app

client = TestClient(app)

def test_chat_completions():
    """Test /v1/chat/completions endpoint."""
    response = client.post("/v1/chat/completions", json={"prompt": "My SIN is 123-456-789 and UCI is 1234567890"})
    assert response.status_code == 200