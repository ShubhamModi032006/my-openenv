import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_reset_creates_session():
    response = client.post("/reset", json={"task_level": "easy"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "observation" in data
    assert "current_email" in data["observation"]

def test_step_requires_valid_session():
    # Invalid session id should return 404
    response = client.post("/step", json={"session_id": "fake_id_123", "action": {"priority": "high"}})
    assert response.status_code == 404

def test_full_workflow():
    res = client.post("/reset", json={"task_level": "easy"})
    session_id = res.json()["session_id"]
    
    # Send a step with the correct session_id
    step_res = client.post("/step", json={
        "session_id": session_id,
        "action": {"priority": "high"}
    })
    
    assert step_res.status_code == 200
    step_data = step_res.json()
    assert "reward" in step_data
    assert "observation" in step_data

def test_state_endpoint():
    res = client.post("/reset", json={"task_level": "easy"})
    session_id = res.json()["session_id"]
    
    state_res = client.get(f"/state?session_id={session_id}")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert "current_index" in state_data
    assert state_data["task_level"] == "easy"
