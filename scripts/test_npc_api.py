#!/usr/bin/env python3
"""
Test script for the Dynamic NPC Generator API functionality
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from npc.dynamic_generator import generate_story_npcs
from db import SessionLocal
from soulmap.service import set_soulmap


async def test_npc_generation():
    """Test NPC generation functionality."""
    
    print("🧪 Testing Dynamic NPC Generator API")
    print("=" * 50)
    
    # Test data
    test_data = {
        "player_id": "api_test_player",
        "player_name": "API Test Player",
        "player_archetype": "Hero",
        "story_theme": "Epic Quest",
        "soul_traits": {
            "COURAGE": 0.9,
            "JUSTICE": 0.8,
            "WISDOM": 0.6,
            "COMPASSION": 0.7,
            "FEAR": -0.3
        }
    }
    
    db = SessionLocal()
    
    try:
        # Set up soul map
        print("📊 Setting up soul map...")
        set_soulmap(db, test_data["player_id"], test_data["soul_traits"])
        print("✅ Soul map created")
        
        # Generate NPCs
        print("🎭 Generating NPCs...")
        npcs = await generate_story_npcs(
            player_id=test_data["player_id"],
            player_name=test_data["player_name"],
            player_archetype=test_data["player_archetype"],
            story_theme=test_data["story_theme"],
            num_npcs=3
        )
        
        print(f"✅ Generated {len(npcs)} NPCs:")
        for i, npc in enumerate(npcs, 1):
            print(f"  {i}. {npc.full_name}")
            print(f"     Role: {npc.role}")
            print(f"     Archetype: {npc.archetype}")
            print(f"     Trust: {npc.baseline_trust:.2f}")
            print(f"     Generated: {npc.generated}")
            print()
        
        # Test retrieving NPC info
        print("🔍 Testing NPC retrieval...")
        from npc.models import NPC
        stored_npcs = db.query(NPC).filter_by(generated="true").all()
        print(f"✅ Found {len(stored_npcs)} generated NPCs in database")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_npc_generation()) 