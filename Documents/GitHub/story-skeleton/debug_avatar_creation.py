#!/usr/bin/env python3
"""
Debug script to test avatar creation process
"""

import requests
import json

def test_soulseed_endpoint():
    """Test the /soulseed endpoint directly."""
    print("=== Testing /soulseed endpoint ===")
    
    payload = {
        "playerName": "Hymn",
        "archetypePreset": "Visionary Dreamer",
        "archetypeCustom": None
    }
    
    # Test direct API call
    response = requests.post("http://localhost:8000/soulseed", json=payload)
    print(f"Direct API Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    
    # Test through Vite proxy
    response = requests.post("http://localhost:5173/soulseed", json=payload)
    print(f"Vite Proxy Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")

def test_avatar_upload():
    """Test the /avatar/upload endpoint."""
    print("\n=== Testing /avatar/upload endpoint ===")
    
    # Create a simple test file
    files = {
        'file': ('test.jpg', b'fake image data', 'image/jpeg'),
        'playerId': (None, 'hymn')
    }
    
    response = requests.post("http://localhost:8000/avatar/upload", files=files)
    print(f"Avatar Upload Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")

def test_frontend_health():
    """Test if the frontend is accessible."""
    print("\n=== Testing Frontend Health ===")
    
    try:
        response = requests.get("http://localhost:5173")
        print(f"Frontend Status: {response.status_code}")
        if response.status_code == 200:
            print("Frontend is accessible")
        else:
            print(f"Frontend error: {response.text}")
    except Exception as e:
        print(f"Frontend connection error: {e}")

def test_api_health():
    """Test API health."""
    print("\n=== Testing API Health ===")
    
    response = requests.get("http://localhost:8000/health")
    print(f"API Health Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"API Status: {data['status']}")
        print(f"Services: {data['services']}")
    else:
        print(f"API Health Error: {response.text}")

if __name__ == "__main__":
    print("🔍 Avatar Creation Debug")
    print("=" * 50)
    
    test_api_health()
    test_frontend_health()
    test_soulseed_endpoint()
    test_avatar_upload()
    
    print("\n🎯 Debug Complete!")
    print("\nIf all tests pass, the issue might be:")
    print("- JavaScript error in the frontend")
    print("- CORS issue")
    print("- Network connectivity problem")
    print("- Frontend state management issue")
