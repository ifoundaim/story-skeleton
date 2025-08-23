#!/usr/bin/env python3
"""
Test script to trigger consequence events by simulating story choices
"""

import sys
import os
import asyncio
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_consequence_trigger():
    """Test triggering consequence events through the beat_dsl system."""
    
    try:
        from story.beat_dsl import apply_effects
        from story.state import StoryState
        from websocket_manager import websocket_manager
        
        print("✅ Successfully imported modules")
        
        # Create a test story state
        state = StoryState(
            scene_index=5,
            phase="middle",
            tension=0.5,
            target_curve=[0.2] * 30,
            player={"name": "TestPlayer", "theme": "test", "archetype": "warrior"},
            npcs={
                "npc1": {
                    "full_name": "Alice",
                    "role": "Companion",
                    "trust": 0.6,
                    "arc_state": "intro",
                    "interactions": 2,
                },
                "npc2": {
                    "full_name": "Bob",
                    "role": "Mentor",
                    "trust": 0.4,
                    "arc_state": "intro",
                    "interactions": 1,
                }
            },
            party=[],
            flags={},
        )
        
        print("✅ Created test story state")
        
        # Test different consequence types
        test_beats = [
            {
                "name": "Promise Set",
                "effects": {
                    "add_promise": {
                        "id": "promise_1",
                        "description": "Help Alice with her quest",
                        "npc_id": "npc1",
                        "due_by_scene": 10
                    }
                }
            },
            {
                "name": "Trust Change",
                "effects": {
                    "trust[npc]": "+0.1"
                }
            },
            {
                "name": "Flag Set",
                "effects": {
                    "set_flag": {
                        "important_decision": True,
                        "quest_started": False
                    }
                }
            },
            {
                "name": "World Flag",
                "effects": {
                    "set_world_flag": {
                        "world_state": "changed",
                        "global_event": "triggered"
                    }
                }
            },
            {
                "name": "Promise Fulfilled",
                "effects": {
                    "fulfill_promise": "promise_1"
                }
            },
            {
                "name": "Reputation Change",
                "effects": {
                    "reputation_delta": {
                        "bravery": 0.1,
                        "wisdom": -0.05
                    }
                }
            }
        ]
        
        print(f"✅ Created {len(test_beats)} test beats")
        
        # Apply each beat and trigger consequences
        for i, beat in enumerate(test_beats, 1):
            print(f"\n🧪 Testing {beat['name']}...")
            
            try:
                # Apply effects (this should trigger WebSocket events)
                apply_effects(beat, state, ["npc1"], player_id="test_player")
                print(f"✅ Applied effects for {beat['name']}")
                
                # Wait a moment for async events to process
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"❌ Error applying {beat['name']}: {e}")
        
        print("\n🎉 All consequence tests completed!")
        print("💡 Check the frontend and WebSocket test page for toast notifications.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure the backend is running and all modules are available.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Consequence Trigger System")
    print("=" * 50)
    
    # Run the async test
    asyncio.run(test_consequence_trigger())
    
    print("\n" + "=" * 50)
    print("🎉 Test complete!")
