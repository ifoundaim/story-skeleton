import pytest
from fastapi.testclient import TestClient
from backend.main import app
import uuid

# Create a test client
client = TestClient(app)

def test_create_npc_profile():
    """Test creating an NPC profile via API"""
    npc_id = "test_api_npc"
    full_name = "Test API NPC"
    baseline_trust = 0.4
    
    response = client.post("/npc/profile", json={
        "npc_id": npc_id,
        "full_name": full_name,
        "baseline_trust": baseline_trust
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == full_name
    assert data["baseline_trust"] == baseline_trust
    assert data["trust"] == baseline_trust
    assert "id" in data

def test_get_npc_profile():
    """Test getting an NPC profile via API"""
    npc_id = "test_get_npc"
    full_name = "Test Get NPC"
    baseline_trust = 0.6
    
    # First create the NPC
    create_response = client.post("/npc/profile", json={
        "npc_id": npc_id,
        "full_name": full_name,
        "baseline_trust": baseline_trust
    })
    assert create_response.status_code == 200
    
    # Then get it
    get_response = client.get(f"/npc/profile/{npc_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["full_name"] == full_name
    assert data["baseline_trust"] == baseline_trust
    assert data["trust"] == baseline_trust

def test_update_npc_trust():
    """Test updating NPC trust via API"""
    npc_id = "test_trust_npc"
    full_name = "Test Trust NPC"
    baseline_trust = 0.5
    
    # First create the NPC
    create_response = client.post("/npc/profile", json={
        "npc_id": npc_id,
        "full_name": full_name,
        "baseline_trust": baseline_trust
    })
    assert create_response.status_code == 200
    
    # Update trust
    update_response = client.post(f"/npc/profile/{npc_id}/trust?delta=0.3")
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["trust"] == 0.8  # 0.5 + 0.3
    
    # Update trust again (negative)
    update_response2 = client.post(f"/npc/profile/{npc_id}/trust?delta=-0.2")
    assert update_response2.status_code == 200
    data2 = update_response2.json()
    assert data2["trust"] == 0.6  # 0.8 - 0.2

def test_get_all_npc_profiles():
    """Test getting all NPC profiles via API"""
    # Create a few NPCs
    npcs_data = [
        ("test_all_1", "Test All NPC 1", 0.3),
        ("test_all_2", "Test All NPC 2", 0.7),
    ]
    
    for npc_id, full_name, baseline_trust in npcs_data:
        response = client.post("/npc/profile", json={
            "npc_id": npc_id,
            "full_name": full_name,
            "baseline_trust": baseline_trust
        })
        assert response.status_code == 200
    
    # Get all profiles
    response = client.get("/npc/profiles")
    assert response.status_code == 200
    data = response.json()
    
    # Should have at least our test NPCs
    npc_names = [npc["full_name"] for npc in data]
    assert "Test All NPC 1" in npc_names
    assert "Test All NPC 2" in npc_names

def test_npc_profile_idempotent():
    """Test that creating the same NPC profile twice is idempotent"""
    npc_id = "test_idempotent_npc"
    full_name = "Test Idempotent NPC"
    baseline_trust = 0.5
    
    # First creation
    response1 = client.post("/npc/profile", json={
        "npc_id": npc_id,
        "full_name": full_name,
        "baseline_trust": baseline_trust
    })
    assert response1.status_code == 200
    data1 = response1.json()
    original_id = data1["id"]
    
    # Second creation with different values
    response2 = client.post("/npc/profile", json={
        "npc_id": npc_id,
        "full_name": "Different Name",
        "baseline_trust": 0.8
    })
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Should return the same NPC with original values
    assert data2["id"] == original_id
    assert data2["full_name"] == full_name  # Should not change
    assert data2["baseline_trust"] == baseline_trust  # Should not change
    assert data2["trust"] == baseline_trust  # Should not change

def test_nonexistent_npc_profile():
    """Test getting a nonexistent NPC profile returns 404"""
    nonexistent_id = "nonexistent_npc"
    response = client.get(f"/npc/profile/{nonexistent_id}")
    assert response.status_code == 404

def test_update_nonexistent_npc_trust():
    """Test updating trust for nonexistent NPC returns 404"""
    nonexistent_id = "nonexistent_npc"
    response = client.post(f"/npc/profile/{nonexistent_id}/trust?delta=0.1")
    assert response.status_code == 404 