"""
RecruitmentEvaluator - Automatic NPC recruitment choice injection

This module evaluates whether an NPC should be offered recruitment based on:
- Trust level (≥0.60)
- Story timing (Act III or later, scene.index >= 16)
- Narrative context (victory scenes, emotional alignment)
- Cooldown periods (≥2 scenes since last invite)
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session
import uuid

from npc.service import get_npc_by_id, get_trust_scores
from npc.models import NPCState


@dataclass
class RecruitmentEvaluation:
    """Result of recruitment evaluation"""
    should_recruit: bool
    rationale: str
    trust_level: float
    scene_index: int
    npc_id: str
    npc_name: str


class RecruitmentEvaluator:
    """Evaluates whether an NPC should be offered recruitment"""
    
    def __init__(self):
        self.min_trust_threshold = 0.60
        self.min_scene_index = 16  # Act III or later
        self.cooldown_scenes = 2   # Minimum scenes between invites
        
    def evaluate_scene_for_recruitment(
        self,
        scene_tag: str,
        npcs_present: List[str],
        player_id: str,
        player_name: str,
        theme: str,
        intent_vector: List[float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate all NPCs present in a scene for recruitment opportunities for a specific player.
        
        Args:
            scene_tag: Scene identifier
            npcs_present: List of NPC IDs present in the scene
            player_id: Player identifier (required for DB lookups)
            player_name: Player name for personalization
            theme: Story theme
            intent_vector: Player intent vector
            
        Returns:
            Dictionary of recruitment choices to inject
        """
        recruitment_choices = {}
        
        # Extract scene index from tag (e.g., "tag_017" -> 16)
        try:
            scene_index = int(scene_tag.replace("tag_", "")) - 1
        except (ValueError, AttributeError):
            # Fallback if tag parsing fails
            scene_index = 0
        
        scene_data = {
            "scene_index": scene_index,
            "narrative_purpose": "story_progression"  # Default purpose
        }
        
        from db import SessionLocal
        db = SessionLocal()
        
        try:
            for npc_id in npcs_present:
                # Evaluate this NPC for recruitment with real player context
                evaluation = self.evaluate(
                    npc_id,
                    scene_data,
                    player_id,
                    db
                )
                
                if evaluation.should_recruit:
                    # Generate recruitment choice
                    choice_key = f"recruit_{str(npc_id)[:8]}"
                    choice_data = self._generate_recruitment_choice(
                        npc_id,
                        evaluation,
                        player_name,
                        theme
                    )
                    recruitment_choices[choice_key] = choice_data
                    
                    # Mark that we've offered recruitment to this NPC
                    npc = self._get_npc_for_evaluation(player_id, npc_id, db)
                    if npc:
                        self.mark_invite_sent(npc, scene_index, db)
        finally:
            db.close()
        
        return recruitment_choices
    
    def evaluate(
        self, 
        npc_id: str, 
        scene: Dict[str, Any], 
        player_id: str, 
        db: Session,
        player_state: Optional[Dict[str, Any]] = None
    ) -> RecruitmentEvaluation:
        """
        Evaluate whether an NPC should be offered recruitment
        
        Args:
            npc_id: UUID of the NPC to evaluate
            scene: Scene data containing index, narrative_purpose, etc.
            player_id: Player identifier
            db: Database session
            player_state: Optional player state with emotion data
            
        Returns:
            RecruitmentEvaluation with decision and rationale
        """
        # Get NPC data
        npc = get_npc_by_id(player_id, npc_id, db)
        if not npc:
            return RecruitmentEvaluation(
                should_recruit=False,
                rationale="NPC not found in player's world",
                trust_level=0.0,
                scene_index=scene.get("scene_index", 0),
                npc_id=npc_id,
                npc_name="Unknown"
            )
        
        scene_index = scene.get("scene_index", 0)
        trust_level = npc.trust
        
        # Hard checks - these must all pass
        hard_checks = self._evaluate_hard_checks(npc, scene_index, player_id, db)
        if not hard_checks["passed"]:
            return RecruitmentEvaluation(
                should_recruit=False,
                rationale=hard_checks["reason"],
                trust_level=trust_level,
                scene_index=scene_index,
                npc_id=npc_id,
                npc_name=npc.name
            )
        
        # Soft checks - these provide bonus context
        soft_checks = self._evaluate_soft_checks(npc, scene, player_state)
        
        # Combine rationale
        rationale = f"Trust {trust_level:.2f} ≥ {self.min_trust_threshold}, Scene {scene_index} ≥ {self.min_scene_index}"
        if soft_checks["victory_bonus"]:
            rationale += ", Victory scene bonus"
        if soft_checks["emotion_bonus"]:
            rationale += ", Emotional alignment bonus"
        
        return RecruitmentEvaluation(
            should_recruit=True,
            rationale=rationale,
            trust_level=trust_level,
            scene_index=scene_index,
            npc_id=npc_id,
            npc_name=npc.name
        )
    
    def _evaluate_hard_checks(
        self, 
        npc: NPCState, 
        scene_index: int, 
        player_id: str, 
        db: Session
    ) -> Dict[str, Any]:
        """Evaluate hard requirements that must all pass"""
        
        # Check trust threshold
        if npc.trust < self.min_trust_threshold:
            return {
                "passed": False,
                "reason": f"Trust {npc.trust:.2f} below threshold {self.min_trust_threshold}"
            }
        
        # Check scene timing (Act III or later)
        if scene_index < self.min_scene_index:
            return {
                "passed": False,
                "reason": f"Scene {scene_index} too early (need ≥{self.min_scene_index})"
            }
        
        # Check if NPC is already a companion
        if self._is_already_companion(npc, player_id, db):
            return {
                "passed": False,
                "reason": f"{npc.name} is already a companion"
            }
        
        # Check cooldown period
        if not self._check_cooldown(npc, scene_index, db):
            return {
                "passed": False,
                "reason": f"Cooldown active (need ≥{self.cooldown_scenes} scenes since last invite)"
            }
        
        return {"passed": True, "reason": "All hard checks passed"}
    
    def _evaluate_soft_checks(
        self, 
        npc: NPCState, 
        scene: Dict[str, Any], 
        player_state: Optional[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Evaluate soft requirements that provide bonus context"""
        
        victory_bonus = False
        emotion_bonus = False
        
        # Check for victory scene
        narrative_purpose = scene.get("narrative_purpose", "")
        if narrative_purpose.lower() == "victory":
            victory_bonus = True
        
        # Check emotional alignment
        if player_state and "emotion" in player_state:
            player_emotion = player_state["emotion"]
            compatible_emotions = npc.meta.get("compatible_emotions", [])
            
            if player_emotion in compatible_emotions:
                emotion_bonus = True
        
        return {
            "victory_bonus": victory_bonus,
            "emotion_bonus": emotion_bonus
        }
    
    def _is_already_companion(self, npc: NPCState, player_id: str, db: Session) -> bool:
        """Check if NPC is already in player's party"""
        # For now, we'll use a simple check based on meta data
        # In a more sophisticated system, this would check a party/companion table
        return npc.meta.get("is_companion", False)
    
    def _check_cooldown(self, npc: NPCState, current_scene_index: int, db: Session) -> bool:
        """Check if enough scenes have passed since last recruitment offer"""
        last_invite_scene = npc.meta.get("last_invite_scene_index", -1)
        
        if last_invite_scene == -1:
            # Never been invited, so no cooldown
            return True
        
        scenes_since_invite = current_scene_index - last_invite_scene
        return scenes_since_invite >= self.cooldown_scenes
    
    def mark_invite_sent(self, npc: NPCState, scene_index: int, db: Session) -> None:
        """Mark that an invitation was sent to this NPC at the given scene"""
        npc.meta["last_invite_scene_index"] = scene_index
        db.commit()

    def _generate_recruitment_choice(
        self,
        npc_id: str,
        evaluation: RecruitmentEvaluation,
        player_name: str,
        theme: str
    ) -> Dict[str, Any]:
        """
        Generate a recruitment choice object
        
        Args:
            npc_id: NPC identifier
            evaluation: Recruitment evaluation result
            player_name: Player name for personalization
            theme: Story theme
            
        Returns:
            Choice object to inject into scene
        """
        # Generate choice text based on NPC and context
        choice_text = self._generate_choice_text(evaluation, player_name, theme)
        recruit_line = self._generate_recruit_line(evaluation, player_name, theme)
        
        return {
            "text": choice_text,
            "npc_onboard": npc_id,
            "conditions": {
                "trust_above": self.min_trust_threshold,
                "not_companion": True
            },
            "recruit_line": recruit_line,
            "npc_trust_deltas": {
                npc_id: 0.05  # Small trust boost for successful recruitment
            },
            "next": "continue"  # Continue to next scene after recruitment
        }
    
    def _generate_choice_text(
        self,
        evaluation: RecruitmentEvaluation,
        player_name: str,
        theme: str
    ) -> str:
        """Generate the choice text for recruitment"""
        npc_name = evaluation.npc_name
        
        # Different choice texts based on trust level
        if evaluation.trust_level >= 0.8:
            return f"Ask {npc_name} to join your quest as a trusted companion"
        elif evaluation.trust_level >= 0.7:
            return f"Invite {npc_name} to accompany you on your journey"
        else:
            return f"Request {npc_name}'s aid in your mission"
    
    def _generate_recruit_line(
        self,
        evaluation: RecruitmentEvaluation,
        player_name: str,
        theme: str
    ) -> str:
        """Generate the in-character recruitment line"""
        npc_name = evaluation.npc_name
        trust_level = evaluation.trust_level
        
        # Different recruitment lines based on trust level
        if trust_level >= 0.8:
            return f"'{player_name}, I've seen your courage and wisdom. I would be honored to fight alongside you.'"
        elif trust_level >= 0.7:
            return f"'You've proven yourself worthy, {player_name}. I'll join your cause.'"
        else:
            return f"'Very well, {player_name}. I'll help you, but I'm watching you closely.'"
    
    def _get_npc_for_evaluation(self, player_id: str, npc_id: str, db) -> Optional[NPCState]:
        """Get NPC for evaluation using the provided player context"""
        try:
            return get_npc_by_id(player_id, npc_id, db)
        except Exception:
            return None


# Global instance for easy access
evaluator = RecruitmentEvaluator() 