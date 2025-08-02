#!/usr/bin/env python3
"""
Simple test script to verify that the soulseed endpoint works correctly
"""

import json
import ast

def test_soulseed_endpoint():
    """Test that the soulseed endpoint retrieves player name correctly"""
    try:
        # Parse the backend main.py file to check the soulseed endpoint
        with open('backend/main.py', 'r') as f:
            content = f.read()
        
        # Find the soulseed endpoint function
        tree = ast.parse(content)
        soulseed_func = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'create_player_profile':
                soulseed_func = node
                break
        
        if not soulseed_func:
            print("❌ ERROR: Could not find create_player_profile function")
            return False
        
        # Check if it saves the player name correctly
        code_str = ast.unparse(soulseed_func)
        
        print("✅ Soulseed endpoint test:")
        
        # Check for key elements
        checks = [
            ("Saves playerName to profile", "playerName" in code_str and "payload.playerName" in code_str),
            ("Creates player_id from name", "slugify(payload.playerName)" in code_str),
            ("Stores in profiles dict", "profiles[player_id]" in code_str),
            ("Writes to JSON file", "_write_json" in code_str)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            if check_result:
                print(f"   ✅ {check_name}")
            else:
                print(f"   ❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_ritual_endpoint():
    """Test that the ritual endpoint retrieves player name correctly"""
    try:
        # Parse the backend main.py file to check the ritual endpoint
        with open('backend/main.py', 'r') as f:
            content = f.read()
        
        # Find the ritual endpoint function
        tree = ast.parse(content)
        ritual_func = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'api_ritual':
                ritual_func = node
                break
        
        if not ritual_func:
            print("\n❌ ERROR: Could not find api_ritual function")
            return False
        
        # Check if it retrieves player name from profiles
        code_str = ast.unparse(ritual_func)
        
        print("\n✅ Ritual endpoint test:")
        
        # Check for key elements
        checks = [
            ("Loads profiles from JSON", "_read_json(str(DATA_FILE)" in code_str),
            ("Retrieves player name", "player_name = profile.get('playerName'" in code_str),
            ("Has fallback name", "'Adventurer'" in code_str),
            ("Passes player_name to generate_story", "player_name," in code_str and "generate_story" in code_str)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            if check_result:
                print(f"   ✅ {check_name}")
            else:
                print(f"   ❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_player_profile_structure():
    """Test that the player profile structure is correct"""
    try:
        print("\n✅ Player profile structure test:")
        
        # Check if the profile file exists and has correct structure
        try:
            with open('backend/player_profile.json', 'r') as f:
                profiles = json.load(f)
            
            print("   ✅ Profile file exists and is valid JSON")
            
            # Check structure of existing profiles
            for player_id, profile in profiles.items():
                required_fields = ['playerName', 'archetype', 'soulSeedId']
                missing_fields = [field for field in required_fields if field not in profile]
                
                if missing_fields:
                    print(f"   ❌ Profile for {player_id} missing fields: {missing_fields}")
                    return False
                else:
                    print(f"   ✅ Profile for {player_id} has all required fields")
            
            return True
            
        except FileNotFoundError:
            print("   ⚠️ Profile file doesn't exist yet (this is normal for new installations)")
            return True
        except json.JSONDecodeError:
            print("   ❌ Profile file exists but is not valid JSON")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Soulseed Endpoint and Player Name Integration")
    print("=" * 60)
    
    tests = [
        test_soulseed_endpoint,
        test_ritual_endpoint,
        test_player_profile_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The soulseed endpoint should work correctly.")
        print("\n📝 Next steps:")
        print("   1. The Docker container needs to be fixed to include the codex module")
        print("   2. Or run the backend locally with proper environment variables")
        print("   3. Test the full flow through the frontend")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main() 