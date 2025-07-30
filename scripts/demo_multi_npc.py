#!/usr/bin/env python3
"""
Multi-NPC Support Demo Script (SPR-NPC03)

This script demonstrates the new multi-NPC functionality including:
- Multiple NPCs with individual trust tracking
- Group dialogue generation
- Multi-NPC trust delta application
- Frontend integration examples

Run this script to see the multi-NPC system in action.
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "codex"))

def demo_group_dialogue():
    """Demo multi-NPC group dialogue generation"""
    print("=" * 60)
    print("MULTI-NPC GROUP DIALOGUE DEMO")
    print("=" * 60)
    
    try:
        from codex.npc.npc_group_dialogue import (
            generate_group_dialogue,
            generate_group_dialogue_with_context,
            get_trust_dynamic
        )
        
        # Demo 1: Single NPC (backward compatibility)
        print("\n1. Single NPC Dialogue (Backward Compatibility):")
        print("-" * 50)
        single_npc_dialogue = generate_group_dialogue(["lyra"], "demo_player")
        for entry in single_npc_dialogue:
            print(f"  {entry['name']}: \"{entry['text']}\"")
            print(f"  Trust: {entry['trust']:.2f}")
        
        # Demo 2: Multiple NPCs
        print("\n2. Multi-NPC Group Dialogue:")
        print("-" * 50)
        multi_npc_dialogue = generate_group_dialogue(["lyra", "orin"], "demo_player")
        for i, entry in enumerate(multi_npc_dialogue):
            print(f"  {entry['name']}: \"{entry['text']}\"")
            print(f"  Trust: {entry['trust']:.2f}")
            if i < len(multi_npc_dialogue) - 1:
                print()
        
        # Demo 3: Context-aware dialogue
        print("\n3. Context-Aware Group Dialogue:")
        print("-" * 50)
        context_dialogue = generate_group_dialogue_with_context(
            ["lyra", "orin"], 
            "demo_player", 
            "The party faces a dangerous ancient guardian blocking their path."
        )
        for i, entry in enumerate(context_dialogue):
            print(f"  {entry['name']}: \"{entry['text']}\"")
            print(f"  Trust: {entry['trust']:.2f}")
            if i < len(context_dialogue) - 1:
                print()
        
        # Demo 4: Trust dynamics
        print("\n4. Trust Dynamic Classification:")
        print("-" * 50)
        trust_scenarios = [
            ("Both High Trust", {"lyra": 0.8, "orin": 0.9}),
            ("Mixed Trust", {"lyra": 0.8, "orin": 0.2}),
            ("Both Low Trust", {"lyra": 0.1, "orin": 0.2})
        ]
        
        for scenario_name, trust_scores in trust_scenarios:
            dynamic = get_trust_dynamic(trust_scores)
            print(f"  {scenario_name}: {dynamic}")
            for npc_id, trust in trust_scores.items():
                print(f"    {npc_id}: {trust:.1f}")
        
    except Exception as e:
        print(f"Error in group dialogue demo: {e}")
        import traceback
        traceback.print_exc()

def demo_story_integration():
    """Demo story generation with multi-NPC support"""
    print("\n" + "=" * 60)
    print("STORY GENERATION WITH MULTI-NPC SUPPORT")
    print("=" * 60)
    
    try:
        from purpose_agents.generate_story import create_fallback_8_node_story
        
        # Generate a story with multi-NPC features
        story = create_fallback_8_node_story("Ancient Quest", [0.5] * 8)
        
        print("\nStory Structure with NPC Information:")
        print("-" * 50)
        
        for i, (tag, node) in enumerate(list(story.items())[:3]):  # Show first 3 nodes
            print(f"\nNode {i+1} ({tag}):")
            print(f"  NPCs Present: {node.get('npcs_present', 'Not specified')}")
            print(f"  Text: {node.get('text', 'No text')[:100]}...")
            
            choices = node.get('choices', {})
            if choices:
                print("  Choices:")
                for choice_key, choice in choices.items():
                    print(f"    {choice_key}: {choice.get('text', 'No text')[:50]}...")
                    
                    # Show trust deltas
                    if 'trust_delta' in choice:
                        print(f"      Legacy Trust Delta: {choice['trust_delta']}")
                    
                    if 'npc_trust_deltas' in choice:
                        print(f"      Multi-NPC Trust Deltas:")
                        for npc_id, delta in choice['npc_trust_deltas'].items():
                            print(f"        {npc_id}: {delta:+.1f}")
        
        print(f"\nTotal story nodes: {len(story)}")
        
        # Count nodes with multi-NPC features
        nodes_with_npcs = sum(1 for node in story.values() if 'npcs_present' in node)
        choices_with_multi_trust = sum(
            1 for node in story.values() 
            for choice in node.get('choices', {}).values() 
            if 'npc_trust_deltas' in choice
        )
        
        print(f"Nodes with NPC presence: {nodes_with_npcs}")
        print(f"Choices with multi-NPC trust deltas: {choices_with_multi_trust}")
        
    except Exception as e:
        print(f"Error in story integration demo: {e}")
        import traceback
        traceback.print_exc()

def demo_frontend_data_structure():
    """Demo frontend data structures for multi-NPC dialogue"""
    print("\n" + "=" * 60)
    print("FRONTEND DATA STRUCTURE EXAMPLES")
    print("=" * 60)
    
    # Example data structures for frontend
    print("\n1. Legacy Single NPC Props (Backward Compatible):")
    print("-" * 50)
    legacy_props = {
        "avatarUrl": "/companion-avatar.png",
        "npcText": "I trust your judgment completely.",
        "trust": 0.8,
        "npcTextDynamic": "Your courage inspires me!"
    }
    print(json.dumps(legacy_props, indent=2))
    
    print("\n2. Single NPC from Array:")
    print("-" * 50)
    single_npc_array = {
        "npcs": [
            {
                "npc_id": "lyra",
                "name": "Lyra",
                "text": "Your determination fills me with hope.",
                "trust": 0.75,
                "avatarUrl": "/lyra-avatar.png"
            }
        ],
        "groupMode": False
    }
    print(json.dumps(single_npc_array, indent=2))
    
    print("\n3. Multi-NPC Group Mode:")
    print("-" * 50)
    group_mode_props = {
        "npcs": [
            {
                "npc_id": "lyra",
                "name": "Lyra",
                "text": "I believe in your courage!",
                "trust": 0.8,
                "avatarUrl": "/lyra-avatar.png"
            },
            {
                "npc_id": "orin",
                "name": "Orin",
                "text": "Be cautious in your choices.",
                "trust": 0.3,
                "avatarUrl": "/orin-avatar.png"
            }
        ],
        "groupMode": True,
        "npcTextDynamic": "The path ahead is uncertain..."
    }
    print(json.dumps(group_mode_props, indent=2))
    
    print("\n4. API Response Format for Group Dialogue:")
    print("-" * 50)
    api_response = {
        "player_id": "demo_player",
        "npc_ids": ["lyra", "orin"],
        "scene_context": "A tense moment in the forest",
        "dialogue": [
            {
                "npc_id": "lyra",
                "name": "Lyra",
                "text": "Something feels wrong here...",
                "trust": 0.7
            },
            {
                "npc_id": "orin", 
                "name": "Orin",
                "text": "My instincts agree - be careful.",
                "trust": 0.4
            }
        ]
    }
    print(json.dumps(api_response, indent=2))

def demo_trust_color_mapping():
    """Demo trust level to color mapping"""
    print("\n" + "=" * 60)
    print("TRUST COLOR MAPPING SYSTEM")
    print("=" * 60)
    
    trust_levels = [
        (0.9, "Very High Trust"),
        (0.7, "High Trust"),
        (0.5, "Medium Trust"),
        (0.3, "Medium-Low Trust"),
        (0.1, "Low Trust")
    ]
    
    print("\nTrust Level -> Color Mapping:")
    print("-" * 50)
    
    for trust, description in trust_levels:
        if trust >= 0.7:
            color = "#4f8cff (Blue)"
        elif trust >= 0.3:
            color = "#ffa500 (Orange)"
        else:
            color = "#ff6b6b (Red)"
        
        print(f"  {trust:.1f} ({description:15s}) -> {color}")

def main():
    """Run all demos"""
    print("Multi-NPC Support and Group Dialogue Dynamics Demo")
    print("SPR-NPC03 Implementation")
    print("=" * 60)
    
    # Run all demo sections
    demo_group_dialogue()
    demo_story_integration()
    demo_frontend_data_structure()
    demo_trust_color_mapping()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("✅ Multi-NPC dialogue generation")
    print("✅ Individual trust tracking per NPC")
    print("✅ Group dynamics and trust conflicts")
    print("✅ Story integration with NPC presence")
    print("✅ Frontend data structures")
    print("✅ Backward compatibility")
    print("✅ Trust-based color coding")
    
    print("\nNext Steps:")
    print("- Test with actual database connections")
    print("- Integrate with frontend scenes")
    print("- Add more sophisticated dialogue templates")
    print("- Implement NPC personality variations")

if __name__ == "__main__":
    main()