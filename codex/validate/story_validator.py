# codex/validate/story_validator.py
"""
Story Tree Validator & Auto-Healing System

Validates story trees for common issues and provides auto-healing capabilities.
"""

import logging
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

def validate(tree: Dict[str, Any]) -> List[str]:
    """
    Validate a story tree and return a list of issues found.
    
    Args:
        tree: Story tree dictionary with scene tags as keys
        
    Returns:
        List of issue descriptions
    """
    issues = []
    
    if not tree:
        issues.append("Empty story tree")
        return issues
    
    # Check for intro_001 (required starting point)
    if "intro_001" not in tree:
        issues.append("Missing required starting scene 'intro_001'")
    
    # Check for duplicate tags (Python dicts can't have duplicate keys, so this is more for validation)
    # In practice, this would catch issues if the tree was constructed incorrectly
    seen_tags = set()
    for tag in tree.keys():
        if tag in seen_tags:
            issues.append(f"Duplicate tag found: {tag}")
        seen_tags.add(tag)
    
    # Check each node for issues
    referenced_tags = set()
    orphaned_tags = set(tree.keys())
    
    for tag, node in tree.items():
        if not isinstance(node, dict):
            issues.append(f"Node {tag} is not a dictionary")
            continue
            
        # Check for missing text
        if "text" not in node or not node["text"]:
            issues.append(f"Missing or empty text in node {tag}")
        elif node["text"] == "[Placeholder text]":
            issues.append(f"Placeholder text found in node {tag}")
            
        # Check choices structure
        choices = node.get("choices", {})
        if not isinstance(choices, dict):
            issues.append(f"Invalid choices structure in node {tag}")
            continue
            
        # Check each choice
        for choice_key, choice_data in choices.items():
            if not isinstance(choice_data, dict):
                issues.append(f"Invalid choice structure in node {tag}, choice {choice_key}")
                continue
                
            # Check for missing choice text
            if "text" not in choice_data or not choice_data["text"]:
                issues.append(f"Missing or empty choice text in node {tag}, choice {choice_key}")
            elif choice_data["text"] == "[Placeholder text]":
                issues.append(f"Placeholder text found in choice {tag}/{choice_key}")
                
            # Check for missing next target
            if "next" not in choice_data:
                issues.append(f"Missing 'next' target in choice {tag}/{choice_key}")
            else:
                next_tag = choice_data["next"]
                referenced_tags.add(next_tag)
                # Check if target exists
                if next_tag not in tree:
                    issues.append(f"Choice {tag}/{choice_key} points to undefined target: {next_tag}")
    
    # Find orphaned scenes (not reachable from intro_001)
    if "intro_001" in tree:
        reachable = _find_reachable_nodes(tree, "intro_001")
        orphaned = orphaned_tags - reachable
        for orphan in orphaned:
            issues.append(f"Orphaned scene not reachable from intro_001: {orphan}")
    
    return issues

def auto_heal(tree: Dict[str, Any], aggressive: bool = False) -> Dict[str, Any]:
    """
    Auto-heal a story tree by fixing common issues.
    
    Args:
        tree: Story tree dictionary to heal
        aggressive: If True, perform more aggressive healing (pruning orphaned nodes)
        
    Returns:
        Healed story tree
    """
    if not tree:
        return tree
    
    healed_tree = tree.copy()
    
    # Ensure intro_001 exists
    if "intro_001" not in healed_tree:
        logger.warning("Creating missing intro_001 scene")
        healed_tree["intro_001"] = {
            "text": "Welcome to your adventure. Your journey begins here.",
            "choices": {
                "1": {"text": "Begin the adventure", "next": "tag_001"}
            },
            "media": {"images": [], "audio": []},
            "npc_text": ""
        }
    
    # Fix missing text with placeholder
    # Create a list of items to avoid modification during iteration
    tree_items = list(healed_tree.items())
    for tag, node in tree_items:
        if not isinstance(node, dict):
            continue
            
        if "text" not in node or not node["text"]:
            node["text"] = "[Placeholder text]"
            logger.warning(f"Added placeholder text to node {tag}")
            
        # Ensure choices structure exists
        if "choices" not in node:
            node["choices"] = {}
            
        # Fix choice issues
        choices = node.get("choices", {})
        if not isinstance(choices, dict):
            node["choices"] = {}
            choices = node["choices"]
            
        for choice_key, choice_data in list(choices.items()):
            if not isinstance(choice_data, dict):
                # Remove invalid choice
                del choices[choice_key]
                logger.warning(f"Removed invalid choice {tag}/{choice_key}")
                continue
                
            # Fix missing choice text
            if "text" not in choice_data or not choice_data["text"]:
                choice_data["text"] = "[Placeholder text]"
                logger.warning(f"Added placeholder text to choice {tag}/{choice_key}")
                
            # Fix missing next target
            if "next" not in choice_data:
                # Create a reasonable next target
                next_tag = _generate_next_tag(healed_tree, tag)
                choice_data["next"] = next_tag
                logger.warning(f"Added missing next target to choice {tag}/{choice_key}: {next_tag}")
                
                # Create the target node if it doesn't exist
                if next_tag not in healed_tree:
                    healed_tree[next_tag] = _create_default_node(next_tag)
    
    # Fix undefined choice targets
    # Create a list of items to avoid modification during iteration
    tree_items = list(healed_tree.items())
    for tag, node in tree_items:
        if not isinstance(node, dict):
            continue
            
        choices = node.get("choices", {})
        for choice_key, choice_data in choices.items():
            if not isinstance(choice_data, dict):
                continue
                
            next_tag = choice_data.get("next")
            if next_tag and next_tag not in healed_tree:
                # Create the missing target node
                healed_tree[next_tag] = _create_default_node(next_tag)
                logger.warning(f"Created missing target node: {next_tag}")
    
    # Aggressive pruning of orphaned nodes
    if aggressive and "intro_001" in healed_tree:
        reachable = _find_reachable_nodes(healed_tree, "intro_001")
        orphaned = set(healed_tree.keys()) - reachable
        
        for orphan in orphaned:
            del healed_tree[orphan]
            logger.warning(f"Aggressively pruned orphaned node: {orphan}")
    
    # Ensure required fields exist
    for tag, node in healed_tree.items():
        if not isinstance(node, dict):
            continue
            
        node.setdefault("media", {"images": [], "audio": []})
        node.setdefault("npc_text", "")
        
        # Ensure choices have required fields
        for choice_data in node.get("choices", {}).values():
            if isinstance(choice_data, dict):
                choice_data.setdefault("trust_delta", 0.0)
    
    return healed_tree

def _find_reachable_nodes(tree: Dict[str, Any], start_tag: str) -> Set[str]:
    """
    Find all nodes reachable from a starting tag using DFS.
    
    Args:
        tree: Story tree dictionary
        start_tag: Starting tag to search from
        
    Returns:
        Set of reachable tag names
    """
    if start_tag not in tree:
        return set()
    
    reachable = set()
    stack = [start_tag]
    
    while stack:
        current_tag = stack.pop()
        if current_tag in reachable:
            continue
            
        reachable.add(current_tag)
        node = tree.get(current_tag, {})
        
        if not isinstance(node, dict):
            continue
            
        choices = node.get("choices", {})
        if not isinstance(choices, dict):
            continue
        for choice_data in choices.values():
            if isinstance(choice_data, dict) and "next" in choice_data:
                next_tag = choice_data["next"]
                if next_tag in tree and next_tag not in reachable:
                    stack.append(next_tag)
    
    return reachable

def _generate_next_tag(tree: Dict[str, Any], current_tag: str) -> str:
    """
    Generate a reasonable next tag name.
    
    Args:
        tree: Story tree dictionary
        current_tag: Current tag name
        
    Returns:
        Generated next tag name
    """
    # Try to extract number from current tag
    if "_" in current_tag:
        try:
            base, num_str = current_tag.rsplit("_", 1)
            num = int(num_str)
            next_num = num + 1
            return f"{base}_{next_num:03d}"
        except (ValueError, IndexError):
            pass
    
    # Fallback: use tag_ prefix with next available number
    existing_nums = set()
    for tag in tree.keys():
        if tag.startswith("tag_"):
            try:
                num = int(tag[4:])
                existing_nums.add(num)
            except ValueError:
                pass
    
    next_num = max(existing_nums, default=0) + 1
    return f"tag_{next_num:03d}"

def _create_default_node(tag: str) -> Dict[str, Any]:
    """
    Create a default node structure.
    
    Args:
        tag: Tag name for the node
        
    Returns:
        Default node dictionary
    """
    return {
        "text": f"[Placeholder text for {tag}]",
        "choices": {},
        "media": {"images": [], "audio": []},
        "npc_text": ""
    } 