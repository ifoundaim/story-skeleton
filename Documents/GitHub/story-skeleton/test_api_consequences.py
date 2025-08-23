#!/usr/bin/env python3
"""
Test script to demonstrate the Consequence Fabric API functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api_health():
    """Test API health endpoint."""
    print("=== Testing API Health ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"API Status: {data['status']}")
        print(f"Services: {data['services']}")
        return True
    return False

def test_start_game():
    """Test starting a new game."""
    print("\n=== Testing Game Start ===")
    payload = {
        "player_name": "ConsequenceTestPlayer",
        "theme": "bond",
        "archetype": "Hero",
        "soulSeedId": "test_consequence_seed"
    }
    
    response = requests.post(f"{BASE_URL}/start", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Scene: {data['sceneTag']}")
        print(f"Text: {data['text'][:100]}...")
        print(f"Choices: {len(data['choices'])}")
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_flow_summary(player_id):
    """Test the flow summary endpoint."""
    print(f"\n=== Testing Flow Summary for {player_id} ===")
    
    response = requests.get(f"{BASE_URL}/flow/summary?player_id={player_id}&chapter=1")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Scene Range: {data['scene_range']}")
        print(f"Choices: {len(data['choices'])}")
        print(f"Consequences: {len(data['consequences'])}")
        print(f"Fogged Branches: {data['fogged_branches']}")
        print(f"Percent Stats: {data['percent_stats']}")
        
        # Show some details
        if data['choices']:
            print(f"\nFirst Choice: {data['choices'][0]}")
        if data['consequences']:
            print(f"\nFirst Consequence: {data['consequences'][0]}")
        
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_consequence_telemetry():
    """Test consequence telemetry logging."""
    print("\n=== Testing Consequence Telemetry ===")
    
    # This would normally be called by the story engine
    # For testing, we'll simulate a consequence change
    from backend.story.telemetry import log_consequence_change
    
    changes = {
        "world_flags": {"city_saved": True},
        "promises": {"fulfilled": ["save_city"]},
        "reputation": {"loyal": 0.2},
        "resources": {"supplies": -3}
    }
    
    log_consequence_change(10, changes)
    print("✅ Consequence telemetry logged")

def test_beat_with_consequences():
    """Test making a choice that has consequences."""
    print("\n=== Testing Beat with Consequences ===")
    
    # First start a game
    game_data = test_start_game()
    if not game_data:
        return
    
    # Make a choice
    choice_payload = {
        "player_id": "ConsequenceTestPlayer",
        "choice_tag": "1"  # Choose the mysterious cave
    }
    
    response = requests.post(f"{BASE_URL}/choose", json=choice_payload)
    print(f"Choice Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Next Scene: {data['sceneTag']}")
        print(f"Text: {data['text'][:100]}...")
        print(f"Choices: {len(data['choices'])}")
        return data
    else:
        print(f"Error: {response.text}")
        return None

def main():
    """Run all API tests."""
    print("🎭 Consequence Fabric API Demo")
    print("=" * 50)
    
    # Test API health
    if not test_api_health():
        print("❌ API not healthy, stopping tests")
        return
    
    # Test telemetry
    test_consequence_telemetry()
    
    # Test game start
    game_data = test_start_game()
    if not game_data:
        print("❌ Could not start game, stopping tests")
        return
    
    # Test flow summary
    test_flow_summary("ConsequenceTestPlayer")
    
    # Test making a choice
    choice_data = test_beat_with_consequences()
    if choice_data:
        print("\n✅ Successfully made a choice with consequences!")
    
    print("\n🎉 Consequence Fabric API Demo Complete!")
    print("\nThe API provides:")
    print("- Game state management with consequence tracking")
    print("- Flow summary endpoint for chapter recaps")
    print("- Telemetry logging for consequence changes")
    print("- Beat selection that considers consequences")

if __name__ == "__main__":
    main()
