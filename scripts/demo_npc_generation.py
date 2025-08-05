#!/usr/bin/env python3
"""
Demo script for the Dynamic NPC Seed Generator & Profile Factory (SPR-NPC06)

This script demonstrates how to generate NPCs dynamically based on player archetype
and soul map data.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from npc.dynamic_generator import generate_story_npcs
from db import SessionLocal
from soulmap.service import get_soulmap_dict, set_soulmap


async def demo_npc_generation():
    """Demonstrate NPC generation for different player archetypes."""
    
    print("🎭 Dynamic NPC Seed Generator & Profile Factory Demo")
    print("=" * 60)
    
    # Test scenarios
    scenarios = [
        {
            "player_id": "demo_hero",
            "player_name": "Alex the Hero",
            "player_archetype": "Hero",
            "story_theme": "Epic Quest",
            "soul_traits": {
                "COURAGE": 0.9,
                "JUSTICE": 0.8,
                "WISDOM": 0.6,
                "COMPASSION": 0.7,
                "FEAR": -0.3
            }
        },
        {
            "player_id": "demo_sage",
            "player_name": "Morgan the Sage",
            "player_archetype": "Sage",
            "story_theme": "Mystical Discovery",
            "soul_traits": {
                "WISDOM": 0.9,
                "CURIOSITY": 0.8,
                "COMPASSION": 0.7,
                "CREATIVITY": 0.6,
                "FEAR": 0.2
            }
        },
        {
            "player_id": "demo_explorer",
            "player_name": "Riley the Explorer",
            "player_archetype": "Explorer",
            "story_theme": "Wilderness Adventure",
            "soul_traits": {
                "CURIOSITY": 0.9,
                "COURAGE": 0.7,
                "OPTIMISM": 0.8,
                "RESILIENCE": 0.6,
                "FEAR": -0.2
            }
        }
    ]
    
    db = SessionLocal()
    
    try:
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📖 Scenario {i}: {scenario['player_name']} ({scenario['player_archetype']})")
            print("-" * 50)
            
            # Set up soul map for this player
            set_soulmap(db, scenario['player_id'], scenario['soul_traits'])
            
            # Generate NPCs
            print(f"🎭 Generating NPCs for {scenario['player_name']}...")
            npcs = await generate_story_npcs(
                player_id=scenario['player_id'],
                player_name=scenario['player_name'],
                player_archetype=scenario['player_archetype'],
                story_theme=scenario['story_theme'],
                num_npcs=3
            )
            
            print(f"✅ Generated {len(npcs)} NPCs:")
            for npc in npcs:
                # Access attributes before closing the session
                full_name = npc.full_name
                role = npc.role or "Unknown"
                archetype = npc.archetype or "Unknown"
                baseline_trust = npc.baseline_trust
                motivation = npc.motivation or "Unknown"
                personality_traits = npc.personality_traits or []
                secrets = npc.secrets or []
                
                print(f"  • {full_name} ({role})")
                print(f"    Archetype: {archetype}")
                print(f"    Trust: {baseline_trust:.2f}")
                print(f"    Motivation: {motivation}")
                print(f"    Personality: {', '.join(personality_traits[:3])}")
                if secrets:
                    print(f"    Secrets: {len(secrets)} hidden")
                print()
    
    finally:
        db.close()
    
    print("\n🎉 Demo completed!")
    print("\nKey Features Demonstrated:")
    print("• LLM-powered NPC generation based on player archetype")
    print("• Soul map integration for personalized NPCs")
    print("• Rich metadata storage (roles, traits, secrets)")
    print("• Fallback NPCs when LLM is unavailable")
    print("• Database persistence of generated NPCs")


if __name__ == "__main__":
    asyncio.run(demo_npc_generation()) 