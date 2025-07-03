import pytest
from backend.npc.models import NPCState
import uuid

def test_npc_crud_and_trust_clamp(db):
    player_id = "test_player"
    npc_id = uuid.uuid4()
    # Create NPC
    npc = NPCState(id=npc_id, player_id=player_id, name="TestNPC", trust=0.5, meta={})
    db.add(npc)
    db.commit()
    # Fetch
    npcs = db.query(NPCState).filter_by(player_id=player_id).all()
    assert len(npcs) == 1
    assert npcs[0].trust == 0.5
    # Clamp trust to 1.0
    npcs[0].trust = min(max(npcs[0].trust + 1.0, 0.0), 1.0)
    db.commit()
    assert db.query(NPCState).filter_by(id=npc_id).one().trust == 1.0
    # Clamp trust to 0.0
    npcs[0].trust = min(max(npcs[0].trust - 2.0, 0.0), 1.0)
    db.commit()
    assert db.query(NPCState).filter_by(id=npc_id).one().trust == 0.0

def test_npc_api(client):
    player_id = "apitest"
    npc_id = uuid.uuid4()  # Use UUID object, not string
    # POST /npc/update (create)
    resp = client.post("/npc/update", json={"player_id": player_id, "npc_id": str(npc_id), "delta_trust": 0.3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_id"] == player_id
    assert data["trust"] == 0.3
    # POST /npc/update (clamp)
    resp = client.post("/npc/update", json={"player_id": player_id, "npc_id": str(npc_id), "delta_trust": 1.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust"] == 1.0
    # POST /npc/update (clamp below 0)
    resp = client.post("/npc/update", json={"player_id": player_id, "npc_id": str(npc_id), "delta_trust": -2.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["trust"] == 0.0
    # GET /npc/{player_id}
    resp = client.get(f"/npc/{player_id}")
    assert resp.status_code == 200
    npcs = resp.json()
    assert isinstance(npcs, list)
    assert any(npc["id"] == str(npc_id) for npc in npcs)
