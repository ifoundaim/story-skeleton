# purpose_agents/constants.py
"""
Constants for the 30-scene four-act narrative framework.
This defines the structure for SPR-ST02 implementation.
"""

# Feature flag for linear fallback mode
LLM_STORY_DISABLED = "LLM_STORY_DISABLED"

# Total number of scenes in the framework
TOTAL_SCENES = 30

# Act structure (0-indexed)
ACT_BREAKS = {
    "ACT_I_END": 6,      # Scenes 0-6: Setup and Introduction
    "ACT_II_END": 15,    # Scenes 7-15: Rising Action and Development
    "ACT_III_END": 23,   # Scenes 16-23: Climax and Crisis
    "ACT_IV_END": 29     # Scenes 24-29: Resolution and Conclusion
}

# Scene ranges for each act
ACT_SCENES = {
    "ACT_I": (0, 6),     # Setup and Introduction
    "ACT_II": (7, 15),   # Rising Action and Development  
    "ACT_III": (16, 23), # Climax and Crisis
    "ACT_IV": (24, 29)   # Resolution and Conclusion
}

# Narrative purposes for each act
ACT_PURPOSES = {
    "ACT_I": {
        "name": "Setup and Introduction",
        "description": "Establish the world, introduce key characters, and set up the central conflict",
        "narrative_goals": [
            "Introduce the protagonist and their world",
            "Establish the central conflict or quest",
            "Introduce key NPCs (Mentor, Guide, early Companions)",
            "Set up the stakes and motivation",
            "Create the initial call to adventure"
        ]
    },
    "ACT_II": {
        "name": "Rising Action and Development",
        "description": "Deepen character relationships, escalate conflicts, and introduce complications",
        "narrative_goals": [
            "Develop relationships with NPCs",
            "Introduce allies and potential rivals",
            "Escalate the central conflict",
            "Present challenges that test the protagonist",
            "Build tension and momentum toward the climax"
        ]
    },
    "ACT_III": {
        "name": "Climax and Crisis",
        "description": "Reach the peak of conflict, face the greatest challenges, and make critical decisions",
        "narrative_goals": [
            "Present the ultimate challenge or confrontation",
            "Force critical character decisions",
            "Reveal major plot twists or revelations",
            "Test all established relationships",
            "Create the darkest moment before resolution"
        ]
    },
    "ACT_IV": {
        "name": "Resolution and Conclusion",
        "description": "Resolve conflicts, show character growth, and provide satisfying conclusions",
        "narrative_goals": [
            "Resolve the central conflict",
            "Show character growth and transformation",
            "Provide closure for NPC relationships",
            "Deliver on the story's themes and promises",
            "Create a satisfying conclusion"
        ]
    }
}

# Scene tag format
def get_scene_tag(scene_index: int) -> str:
    """Generate scene tag for given index (0-29)."""
    return f"tag_{scene_index + 1:03d}"

# NPC placement guidelines per act
NPC_PLACEMENT_GUIDELINES = {
    "ACT_I": {
        "max_npcs_per_scene": 2,
        "primary_roles": ["Mentor", "Guide", "Companion"],
        "introduction_scenes": [0, 2, 4, 6]
    },
    "ACT_II": {
        "max_npcs_per_scene": 3,
        "primary_roles": ["Companion", "Ally", "Rival", "Sage"],
        "introduction_scenes": [7, 10, 13, 15]
    },
    "ACT_III": {
        "max_npcs_per_scene": 3,
        "primary_roles": ["Rival", "Antagonist", "Warrior", "Trickster"],
        "introduction_scenes": [16, 19, 22, 23]
    },
    "ACT_IV": {
        "max_npcs_per_scene": 2,
        "primary_roles": ["Companion", "Ally", "Mentor"],
        "introduction_scenes": [24, 26, 28, 29]
    }
}

# Key story beats and their target scenes
STORY_BEATS = {
    "inciting_incident": [1, 2],      # Early in Act I
    "first_turning_point": [6, 7],    # End of Act I / Start of Act II
    "midpoint": [15, 16],             # End of Act II / Start of Act III
    "second_turning_point": [23, 24], # End of Act III / Start of Act IV
    "climax": [27, 28],               # Late in Act IV
    "resolution": [29]                # Final scene
}

# Choice structure for linear fallback
def get_linear_choice_structure(scene_index: int) -> dict:
    """Generate linear choice structure for fallback mode."""
    if scene_index >= TOTAL_SCENES - 1:
        # Final scene - no choices
        return {}
    
    next_scene = scene_index + 1
    return {
        "1": {
            "text": "Continue your journey",
            "next": get_scene_tag(next_scene)
        }
    } 