import pytest
import uuid
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_import():
    """Test that we can import the module"""
    try:
        from npc.profile_seed import ensure_npc_profile
        print("Import successful")
        assert True
    except Exception as e:
        print(f"Import failed: {e}")
        assert False

if __name__ == "__main__":
    test_import()
    print("Simple test completed") 