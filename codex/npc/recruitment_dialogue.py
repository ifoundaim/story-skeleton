"""
Recruitment dialogue generation for NPC onboarding scenarios.
"""

import random
from typing import List, Dict, Any

# Dialogue templates for different recruitment scenarios
RECRUITMENT_DIALOGUE_TEMPLATES = {
    "friendly": [
        "You've proven yourself trustworthy. I'd be honored to join your companions.",
        "After seeing how you handle yourself, I'd like to be part of your journey.",
        "Your actions speak volumes. I'd be proud to fight alongside you.",
        "You've shown great wisdom and courage. I'd be honored to join your companions.",
        "Your kindness and strength have won me over. I'd like to join your quest."
    ],
    "formal": [
        "I formally request to join your companions. Your leadership is commendable.",
        "After careful consideration, I wish to pledge my service to your cause.",
        "Your noble actions have earned my respect. I offer my allegiance.",
        "I would be honored to serve under your command.",
        "Your quest aligns with my own values. I request to join your companions."
    ],
    "casual": [
        "Hey, you seem like good people. Mind if I tag along?",
        "This looks like it could be fun. Count me in!",
        "You've got a good thing going here. Can I join?",
        "I like your style. Mind if I join your companions?",
        "This seems like my kind of adventure. I'm in!"
    ],
    "reluctant": [
        "I suppose I could help... if you really need it.",
        "Fine, I'll join. But don't expect me to be happy about it.",
        "I guess I don't have much choice. I'll come along.",
        "If you insist, I'll join your companions. But I'm not promising anything.",
        "Alright, I'll help. But only because you seem desperate."
    ]
}

# Success messages for when recruitment is successful
RECRUITMENT_SUCCESS_MESSAGES = [
    "A new bond forms, strengthening your resolve for the journey ahead.",
    "The air seems lighter with this new alliance forged.",
    "Your companions grow stronger with this new companion by your side.",
    "Together, you feel ready to face whatever challenges await."
]

def generate_recruitment_dialogue(npc_name: str, npc_personality: str = "friendly", 
                                context: str = None) -> str:
    """
    Generate recruitment dialogue for an NPC.
    
    Args:
        npc_name: Name of the NPC being recruited
        npc_personality: Personality type (friendly, formal, casual, reluctant)
        context: Optional context for the recruitment
        
    Returns:
        Generated recruitment dialogue
    """
    if npc_personality not in RECRUITMENT_DIALOGUE_TEMPLATES:
        npc_personality = "friendly"
    
    templates = RECRUITMENT_DIALOGUE_TEMPLATES[npc_personality]
    dialogue = random.choice(templates)
    
    # Personalize the dialogue with the NPC's name
    dialogue = dialogue.replace("I", f"{npc_name}")
    
    return dialogue

def generate_recruitment_success_message() -> str:
    """Generate a success message for successful recruitment."""
    return random.choice(RECRUITMENT_SUCCESS_MESSAGES)

def generate_full_recruitment_scene(npc_name: str, npc_personality: str = "friendly",
                                  context: str = None) -> Dict[str, Any]:
    """
    Generate a complete recruitment scene with dialogue and success message.
    
    Args:
        npc_name: Name of the NPC being recruited
        npc_personality: Personality type for dialogue generation
        context: Optional context for the recruitment
        
    Returns:
        Complete recruitment scene data
    """
    recruitment_dialogue = generate_recruitment_dialogue(npc_name, npc_personality, context)
    success_message = generate_recruitment_success_message()
    
    return {
        "npc_name": npc_name,
        "recruitment_dialogue": recruitment_dialogue,
        "success_message": success_message,
        "personality": npc_personality,
        "context": context
    } 