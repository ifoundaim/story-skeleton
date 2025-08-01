import uuid
import json
from backend.npc.service import get_state, apply_trust, onboard_npc
from backend.db import SessionLocal
from codex.npc.group_dialogue import generate_group_dialogue

def demo_multi_npc_interaction():
    """Demonstrate multi-NPC interactions and trust dynamics"""
    
    # Setup test data
    player_id = "demo_player"
    npc_ids = ["lyra", "orin"]
    
    # Initialize database session
    db = SessionLocal()
    
    try:
        # Get current NPC states
        npc_states = get_state(player_id, db)
        print(f"Current NPC states: {len(npc_states)} NPCs found")
        
        # Simulate a group interaction
        context_dialogue = generate_group_dialogue(
            npc_ids, 
            player_id, 
            "The companions face a dangerous ancient guardian blocking their path."
        )
        
        print("\n=== Group Dialogue Generated ===")
        for i, entry in enumerate(context_dialogue):
            print(f"{i+1}. {entry}")
        
        # Simulate trust changes based on dialogue choices
        print("\n=== Simulating Trust Changes ===")
        for npc_id in npc_ids:
            # Apply some trust changes
            trust_change = 0.1 if npc_id == "lyra" else -0.05
            new_trust = apply_trust(player_id, npc_id, trust_change, db)
            print(f"{npc_id}: trust changed by {trust_change}, new trust: {new_trust:.2f}")
        
        # Simulate onboarding an NPC
        print("\n=== Simulating NPC Onboarding ===")
        if "lyra" in npc_ids:
            onboard_npc(player_id, "lyra", db)
            print("Lyra has been onboarded as a companion!")
        
        # Show final states
        final_states = get_state(player_id, db)
        print("\n=== Final NPC States ===")
        for npc in final_states:
            print(f"{npc.name}: trust={npc.trust:.2f}, companion={npc.active_companion}")
            
    finally:
        db.close()

if __name__ == "__main__":
    demo_multi_npc_interaction() 