"""
Dynamic NPC Scene Integration System (SPR-NPC08)

This module integrates dynamically generated NPCs into story scenes based on their
roles, archetypes, and narrative hooks. It provides intelligent NPC placement
throughout the story progression.
"""

import uuid
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from .models import NPC
from .dynamic_generator import generate_story_npcs
from db import SessionLocal


class NPCSceneIntegrator:
    """Integrates dynamically generated NPCs into story scenes."""
    
    def __init__(self):
        self.scene_npc_cache = {}  # Cache NPC assignments per story
        
        # Role-based scene assignment rules
        self.role_assignment_rules = {
            "Mentor": {"acts": [1], "max_per_scene": 1, "priority": 1},
            "Guide": {"acts": [1], "max_per_scene": 1, "priority": 2},
            "Companion": {"acts": [1, 2], "max_per_scene": 2, "priority": 3},
            "Ally": {"acts": [1, 2], "max_per_scene": 2, "priority": 4},
            "Rival": {"acts": [2, 3], "max_per_scene": 1, "priority": 5},
            "Antagonist": {"acts": [2, 3], "max_per_scene": 1, "priority": 6},
            "Sage": {"acts": [1, 2, 3], "max_per_scene": 1, "priority": 7},
            "Warrior": {"acts": [2, 3], "max_per_scene": 1, "priority": 8},
            "Explorer": {"acts": [1, 2], "max_per_scene": 1, "priority": 9},
            "Trickster": {"acts": [2, 3], "max_per_scene": 1, "priority": 10}
        }
    
    async def assign_npcs_to_scenes(
        self,
        player_id: str,
        player_name: str,
        player_archetype: str,
        story_theme: str,
        story_dict: Dict[str, Any],
        num_npcs: int = 3
    ) -> Dict[str, List[str]]:
        """
        Assign dynamically generated NPCs to story scenes.
        
        Args:
            player_id: Player identifier
            player_name: Player's name
            player_archetype: Player's archetype
            story_theme: Story theme
            story_dict: The story dictionary
            num_npcs: Number of NPCs to generate
            
        Returns:
            Dictionary mapping scene tags to NPC IDs
        """
        # Generate NPCs for this story
        npcs = await generate_story_npcs(
            player_id=player_id,
            player_name=player_name,
            player_archetype=player_archetype,
            story_theme=story_theme,
            num_npcs=num_npcs
        )
        
        # Create scene assignment plan
        assignment_plan = self._create_scene_assignment_plan(npcs, story_dict)
        
        # Cache the assignments for this story
        self.scene_npc_cache[player_id] = assignment_plan
        
        return assignment_plan
    
    def _create_scene_assignment_plan(
        self, 
        npcs: List[NPC], 
        story_dict: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Create a plan for assigning NPCs to story scenes.
        
        Args:
            npcs: List of generated NPCs
            story_dict: Story dictionary
            
        Returns:
            Dictionary mapping scene tags to NPC IDs
        """
        scene_tags = list(story_dict.keys())
        total_scenes = len(scene_tags)
        
        # Categorize NPCs by role
        npcs_by_role = self._categorize_npcs_by_role(npcs)
        
        # Create assignment plan
        assignment_plan = {scene_tag: [] for scene_tag in scene_tags}
        
        # Assign NPCs based on progressive introduction and role rules
        for i, scene_tag in enumerate(scene_tags):
            act_number = self._get_act_number(i, total_scenes)
            scene_npcs = []
            
            # Get eligible NPCs for this act
            eligible_npcs = self._get_eligible_npcs_for_act(npcs_by_role, act_number)
            
            # Apply progressive introduction rules
            max_npcs_this_scene = self._get_max_npcs_for_scene(i, total_scenes)
            
            # Select NPCs for this scene
            selected_npcs = self._select_npcs_for_scene(
                eligible_npcs, 
                max_npcs_this_scene, 
                scene_tag,
                story_dict.get(scene_tag, {})
            )
            
            assignment_plan[scene_tag] = [str(npc.id) for npc in selected_npcs]
        
        return assignment_plan
    
    def _categorize_npcs_by_role(self, npcs: List[NPC]) -> Dict[str, List[NPC]]:
        """Categorize NPCs by their roles."""
        categorized = {}
        
        for npc in npcs:
            role = npc.role or "Companion"
            if role not in categorized:
                categorized[role] = []
            categorized[role].append(npc)
        
        return categorized
    
    def _get_act_number(self, scene_index: int, total_scenes: int) -> int:
        """Determine which act a scene belongs to."""
        if total_scenes <= 3:
            return 1
        elif total_scenes <= 6:
            if scene_index < 2:
                return 1
            else:
                return 2
        else:
            if scene_index < 2:
                return 1
            elif scene_index < 4:
                return 2
            else:
                return 3
    
    def _get_eligible_npcs_for_act(
        self, 
        npcs_by_role: Dict[str, List[NPC]], 
        act_number: int
    ) -> List[NPC]:
        """Get NPCs eligible for a specific act based on role rules."""
        eligible = []
        
        for role, npc_list in npcs_by_role.items():
            if role in self.role_assignment_rules:
                rule = self.role_assignment_rules[role]
                if act_number in rule["acts"]:
                    eligible.extend(npc_list)
        
        return eligible
    
    def _get_max_npcs_for_scene(self, scene_index: int, total_scenes: int) -> int:
        """Determine maximum NPCs for a scene based on progressive introduction."""
        if scene_index == 0:
            return 1  # Opening scene - introduce one NPC
        elif scene_index < total_scenes // 2:
            return 2  # Early/mid scenes - up to 2 NPCs
        else:
            return 3  # Later scenes - up to 3 NPCs for group dynamics
    
    def _select_npcs_for_scene(
        self,
        eligible_npcs: List[NPC],
        max_npcs: int,
        scene_tag: str,
        scene_data: Dict[str, Any]
    ) -> List[NPC]:
        """
        Select NPCs for a specific scene based on narrative hooks and role priority.
        
        Args:
            eligible_npcs: List of NPCs eligible for this scene
            max_npcs: Maximum number of NPCs for this scene
            scene_tag: Scene identifier
            scene_data: Scene data dictionary
            
        Returns:
            List of selected NPCs
        """
        if not eligible_npcs:
            return []
        
        selected = []
        
        # Sort NPCs by priority (mentors first, then companions, etc.)
        sorted_npcs = sorted(
            eligible_npcs,
            key=lambda npc: self.role_assignment_rules.get(npc.role or "Companion", {}).get("priority", 999)
        )
        
        # Check for narrative hook matches
        scene_text = scene_data.get("text", "").lower()
        scene_choices = scene_data.get("choices", {})
        choice_texts = [choice.get("text", "").lower() for choice in scene_choices.values()]
        
        # Prioritize NPCs whose narrative hooks match the scene
        hook_matches = []
        other_npcs = []
        
        for npc in sorted_npcs:
            if self._narrative_hooks_match_scene(npc, scene_text, choice_texts):
                hook_matches.append(npc)
            else:
                other_npcs.append(npc)
        
        # Select NPCs: hook matches first, then others
        for npc in hook_matches + other_npcs:
            if len(selected) >= max_npcs:
                break
            
            # Check role limits
            role = npc.role or "Companion"
            role_count = sum(1 for selected_npc in selected if selected_npc.role == role)
            
            if role_count < self.role_assignment_rules.get(role, {}).get("max_per_scene", 1):
                selected.append(npc)
        
        return selected
    
    def _narrative_hooks_match_scene(
        self,
        npc: NPC,
        scene_text: str,
        choice_texts: List[str]
    ) -> bool:
        """
        Check if NPC's narrative hooks match the scene context.
        
        Args:
            npc: NPC to check
            scene_text: Scene description text
            choice_texts: List of choice texts
            
        Returns:
            True if narrative hooks match scene context
        """
        if not npc.narrative_hooks:
            return False
        
        # Convert scene and choice texts to searchable format
        all_text = f"{scene_text} {' '.join(choice_texts)}".lower()
        
        # Check if any narrative hook keywords appear in the scene
        for hook in npc.narrative_hooks:
            hook_lower = hook.lower()
            
            # Simple keyword matching (could be enhanced with NLP)
            keywords = [
                "secret", "knowledge", "ancient", "mystery", "treasure",
                "danger", "challenge", "test", "choice", "decision",
                "help", "guide", "teach", "learn", "discover",
                "fight", "battle", "conflict", "rival", "enemy",
                "friend", "companion", "ally", "mentor", "student"
            ]
            
            for keyword in keywords:
                if keyword in hook_lower and keyword in all_text:
                    return True
        
        return False
    
    def get_npcs_for_scene(self, player_id: str, scene_tag: str) -> List[str]:
        """
        Get NPCs assigned to a specific scene.
        
        Args:
            player_id: Player identifier
            scene_tag: Scene tag
            
        Returns:
            List of NPC IDs for the scene
        """
        if player_id in self.scene_npc_cache:
            return self.scene_npc_cache[player_id].get(scene_tag, [])
        return []
    
    def get_npc_context_for_scene(
        self, 
        player_id: str, 
        scene_tag: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get detailed NPC context for a scene.
        
        Args:
            player_id: Player identifier
            scene_tag: Scene tag
            db: Database session
            
        Returns:
            Dictionary with NPC context information
        """
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            npc_ids = self.get_npcs_for_scene(player_id, scene_tag)
            npc_context = {
                "npcs_present": npc_ids,
                "npc_details": []
            }
            
            for npc_id in npc_ids:
                npc = db.query(NPC).filter_by(id=npc_id).first()
                if npc:
                    npc_context["npc_details"].append({
                        "id": str(npc.id),
                        "full_name": npc.full_name,
                        "role": npc.role,
                        "archetype": npc.archetype,
                        "trust": npc.trust,
                        "personality_traits": npc.personality_traits,
                        "narrative_hooks": npc.narrative_hooks,
                        "motivation": npc.motivation,
                        "relationship_to_player": npc.relationship_to_player
                    })
            
            return npc_context
            
        finally:
            if should_close:
                db.close()


# Global instance for easy access
npc_integrator = NPCSceneIntegrator()


async def assign_npcs_to_scenes(
    player_id: str,
    player_name: str,
    player_archetype: str,
    story_theme: str,
    story_dict: Dict[str, Any],
    num_npcs: int = 3
) -> Dict[str, List[str]]:
    """
    Convenience function to assign NPCs to scenes.
    
    Args:
        player_id: Player identifier
        player_name: Player's name
        player_archetype: Player's archetype
        story_theme: Story theme
        story_dict: Story dictionary
        num_npcs: Number of NPCs to generate
        
    Returns:
        Dictionary mapping scene tags to NPC IDs
    """
    return await npc_integrator.assign_npcs_to_scenes(
        player_id, player_name, player_archetype, story_theme, story_dict, num_npcs
    )


def get_scene_npcs(player_id: str, scene_tag: str) -> List[str]:
    """
    Get NPCs for a specific scene.
    
    Args:
        player_id: Player identifier
        scene_tag: Scene tag
        
    Returns:
        List of NPC IDs for the scene
    """
    return npc_integrator.get_npcs_for_scene(player_id, scene_tag)


def get_scene_npc_context(player_id: str, scene_tag: str) -> Dict[str, Any]:
    """
    Get detailed NPC context for a scene.
    
    Args:
        player_id: Player identifier
        scene_tag: Scene tag
        
    Returns:
        Dictionary with NPC context information
    """
    return npc_integrator.get_npc_context_for_scene(player_id, scene_tag) 