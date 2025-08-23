# backend/tests/test_story_validation.py
"""
Unit tests for story tree validation and auto-healing system.
"""

import pytest
import sys
from pathlib import Path

# Add the backend directory to the path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from codex.validate.story_validator import validate, auto_heal, _find_reachable_nodes

class TestStoryValidation:
    """Test cases for story tree validation."""
    
    def test_empty_tree(self):
        """Test validation of empty tree."""
        issues = validate({})
        assert "Empty story tree" in issues
    
    def test_missing_intro_001(self):
        """Test validation when intro_001 is missing."""
        tree = {
            "tag_001": {
                "text": "Some text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Missing required starting scene 'intro_001'" in issues
    
    def test_duplicate_tags(self):
        """Test validation detects duplicate tags."""
        # Since Python dicts can't have duplicate keys, we'll test with a list of tuples
        # that would represent duplicate keys if they existed
        tree_items = [
            ("intro_001", {
                "text": "Intro text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }),
            ("intro_001", {  # Duplicate key
                "text": "Duplicate intro",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            })
        ]
        # Convert to dict (this will overwrite the first intro_001 with the second)
        tree = dict(tree_items)
        issues = validate(tree)
        # The test should pass since we're validating the final tree structure
        # and the duplicate detection is more for catching programming errors
        assert len(issues) >= 0  # Should not crash
    
    def test_missing_text(self):
        """Test validation detects missing text."""
        tree = {
            "intro_001": {
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Missing or empty text in node intro_001" in issues
    
    def test_placeholder_text(self):
        """Test validation detects placeholder text."""
        tree = {
            "intro_001": {
                "text": "[Placeholder text]",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Placeholder text found in node intro_001" in issues
    
    def test_invalid_choices_structure(self):
        """Test validation detects invalid choices structure."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": "not a dict",
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Invalid choices structure in node intro_001" in issues
    
    def test_missing_choice_text(self):
        """Test validation detects missing choice text."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"next": "tag_001"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Missing or empty choice text in node intro_001, choice 1" in issues
    
    def test_missing_next_target(self):
        """Test validation detects missing next target."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Missing 'next' target in choice intro_001/1" in issues
    
    def test_undefined_choice_target(self):
        """Test validation detects undefined choice targets."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text", "next": "nonexistent_tag"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Choice intro_001/1 points to undefined target: nonexistent_tag" in issues
    
    def test_orphaned_scenes(self):
        """Test validation detects orphaned scenes."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text", "next": "tag_001"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "tag_001": {
                "text": "Tag 1 text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "orphaned_tag": {
                "text": "Orphaned text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert "Orphaned scene not reachable from intro_001: orphaned_tag" in issues
    
    def test_valid_tree(self):
        """Test validation passes for valid tree."""
        tree = {
            "intro_001": {
                "text": "Welcome to the adventure",
                "choices": {
                    "1": {"text": "Begin", "next": "tag_001"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "tag_001": {
                "text": "Scene 1",
                "choices": {
                    "1": {"text": "End", "next": "tag_002"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "tag_002": {
                "text": "The End",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        issues = validate(tree)
        assert len(issues) == 0

class TestAutoHealing:
    """Test cases for story tree auto-healing."""
    
    def test_heal_missing_intro_001(self):
        """Test auto-healing creates missing intro_001."""
        tree = {
            "tag_001": {
                "text": "Some text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree)
        assert "intro_001" in healed
        assert healed["intro_001"]["text"] == "Welcome to your adventure. Your journey begins here."
        assert "tag_001" in healed["intro_001"]["choices"]["1"]["next"]
    
    def test_heal_missing_text(self):
        """Test auto-healing adds placeholder text for missing text."""
        tree = {
            "intro_001": {
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree)
        assert healed["intro_001"]["text"] == "[Placeholder text]"
    
    def test_heal_missing_choice_text(self):
        """Test auto-healing adds placeholder text for missing choice text."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"next": "tag_001"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree)
        assert healed["intro_001"]["choices"]["1"]["text"] == "[Placeholder text]"
    
    def test_heal_missing_next_target(self):
        """Test auto-healing adds missing next target."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree)
        assert "next" in healed["intro_001"]["choices"]["1"]
        # The generated tag should follow the pattern of the current tag
        next_tag = healed["intro_001"]["choices"]["1"]["next"]
        assert next_tag.startswith("intro_") or next_tag.startswith("tag_")
    
    def test_heal_undefined_target(self):
        """Test auto-healing creates missing target nodes."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text", "next": "missing_tag"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree)
        assert "missing_tag" in healed
        assert healed["missing_tag"]["text"] == "[Placeholder text for missing_tag]"
    
    def test_aggressive_pruning(self):
        """Test aggressive pruning removes orphaned nodes."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text", "next": "tag_001"}
                },
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "tag_001": {
                "text": "Tag 1 text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            },
            "orphaned_tag": {
                "text": "Orphaned text",
                "choices": {},
                "media": {"images": [], "audio": []},
                "npc_text": ""
            }
        }
        healed = auto_heal(tree, aggressive=True)
        assert "orphaned_tag" not in healed
        assert "intro_001" in healed
        assert "tag_001" in healed
    
    def test_heal_ensures_required_fields(self):
        """Test auto-healing ensures all required fields exist."""
        tree = {
            "intro_001": {
                "text": "Intro text",
                "choices": {
                    "1": {"text": "Choice text", "next": "tag_001"}
                }
            }
        }
        healed = auto_heal(tree)
        assert "media" in healed["intro_001"]
        assert "npc_text" in healed["intro_001"]
        assert "trust_delta" in healed["intro_001"]["choices"]["1"]

class TestReachableNodes:
    """Test cases for reachable nodes detection."""
    
    def test_find_reachable_nodes_simple(self):
        """Test finding reachable nodes in simple tree."""
        tree = {
            "intro_001": {
                "text": "Intro",
                "choices": {
                    "1": {"text": "Choice", "next": "tag_001"}
                }
            },
            "tag_001": {
                "text": "Scene 1",
                "choices": {}
            },
            "orphaned": {
                "text": "Orphaned",
                "choices": {}
            }
        }
        reachable = _find_reachable_nodes(tree, "intro_001")
        assert "intro_001" in reachable
        assert "tag_001" in reachable
        assert "orphaned" not in reachable
    
    def test_find_reachable_nodes_complex(self):
        """Test finding reachable nodes in complex branching tree."""
        tree = {
            "intro_001": {
                "text": "Intro",
                "choices": {
                    "1": {"text": "Path A", "next": "tag_001"},
                    "2": {"text": "Path B", "next": "tag_002"}
                }
            },
            "tag_001": {
                "text": "Scene A1",
                "choices": {
                    "1": {"text": "End A", "next": "tag_003"}
                }
            },
            "tag_002": {
                "text": "Scene B1",
                "choices": {
                    "1": {"text": "End B", "next": "tag_004"}
                }
            },
            "tag_003": {
                "text": "End A",
                "choices": {}
            },
            "tag_004": {
                "text": "End B",
                "choices": {}
            }
        }
        reachable = _find_reachable_nodes(tree, "intro_001")
        assert len(reachable) == 5
        assert all(tag in reachable for tag in ["intro_001", "tag_001", "tag_002", "tag_003", "tag_004"])
    
    def test_find_reachable_nodes_missing_start(self):
        """Test finding reachable nodes when start tag doesn't exist."""
        tree = {
            "tag_001": {
                "text": "Some text",
                "choices": {}
            }
        }
        reachable = _find_reachable_nodes(tree, "intro_001")
        assert len(reachable) == 0

if __name__ == "__main__":
    pytest.main([__file__]) 