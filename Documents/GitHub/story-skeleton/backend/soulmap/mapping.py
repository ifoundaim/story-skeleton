from enum import Enum
from typing import Dict, List
import numpy as np

VECTOR_SIZE = 64

class SoulTrait(Enum):
    # Core Virtues (0-7)
    COURAGE = 0
    COMPASSION = 1
    WISDOM = 2
    CREATIVITY = 3
    JUSTICE = 4
    TEMPERANCE = 5
    RESILIENCE = 6
    EMPATHY = 7
    
    # Shadow Traits (8-12)
    FEAR = 8
    PRIDE = 9
    APATHY = 10
    SHADOW_BLEND_1 = 11
    SHADOW_BLEND_2 = 12
    SHADOW_BLEND_3 = 13
    SHADOW_BLEND_4 = 14
    SHADOW_BLEND_5 = 15
    
    # Motivations (16-23)
    SELFACTUALIZATION = 16
    EXTERNALVALIDATION = 17
    COLLECTIVE = 18
    MOTIVATION_BLEND_1 = 19
    MOTIVATION_BLEND_2 = 20
    MOTIVATION_BLEND_3 = 21
    MOTIVATION_BLEND_4 = 22
    MOTIVATION_BLEND_5 = 23
    
    # Archetypes (24-31)
    HERO = 24
    REBEL = 25
    SAGE = 26
    CAREGIVER = 27
    MAGICIAN = 28
    LOVER = 29
    SOVEREIGN = 30
    EXPLORER = 31
    
    # Archetype Blends (32-39)
    ARCHETYPE_BLEND_1 = 32
    ARCHETYPE_BLEND_2 = 33
    ARCHETYPE_BLEND_3 = 34
    ARCHETYPE_BLEND_4 = 35
    ARCHETYPE_BLEND_5 = 36
    ARCHETYPE_BLEND_6 = 37
    ARCHETYPE_BLEND_7 = 38
    ARCHETYPE_BLEND_8 = 39
    
    # Cognitive Functions (40-47)
    INTROVERTEDTHINKING = 40
    EXTRAVERTEDTHINKING = 41
    INTROVERTEDFEELING = 42
    EXTRAVERTEDFEELING = 43
    INTROVERTEDSENSING = 44
    EXTRAVERTEDSENSING = 45
    INTROVERTEDINTUITING = 46
    EXTRAVERTEDINTUITING = 47
    
    # Attachment Styles (48-51)
    SECUREATTACHMENT = 48
    ANXIOUSATTACHMENT = 49
    AVOIDANTATTACHMENT = 50
    DISORGANIZEDATTACHMENT = 51
    
    # Psychological Needs (52-59)
    AUTONOMY = 52
    COMPETENCE = 53
    RELATEDNESS = 54
    SELFCONTROL = 55
    MINDFULNESS = 56
    GRIT = 57
    CURIOSITY = 58
    PLAYFULNESS = 59
    
    # Social Traits (60-63)
    OPTIMISM = 60
    VIGILANCE = 61
    SOCIALDOMINANCE = 62
    HUMILITY = 63

def vec_to_dict(vector: List[float]) -> Dict[str, float]:
    """Convert 64-dimensional vector to trait dictionary."""
    if len(vector) != VECTOR_SIZE:
        raise ValueError(f"Vector must have {VECTOR_SIZE} dimensions, got {len(vector)}")
    
    return {trait.name: vector[trait.value] for trait in SoulTrait}

def dict_to_vec(trait_dict: Dict[str, float]) -> List[float]:
    """Convert trait dictionary to 64-dimensional vector."""
    vector = [0.0] * VECTOR_SIZE
    
    for trait_name, value in trait_dict.items():
        try:
            trait = SoulTrait[trait_name]
            vector[trait.value] = float(value)
        except KeyError:
            # Skip unknown traits
            continue
    
    return vector

def clip_vector(vector: List[float], min_val: float = -1.0, max_val: float = 1.0) -> List[float]:
    """Clip vector values to specified range."""
    return [max(min_val, min(max_val, float(x))) for x in vector]

def add_vectors(a: List[float], b: List[float]) -> List[float]:
    """Add two vectors element-wise."""
    if len(a) != len(b):
        raise ValueError(f"Vectors must have same length, got {len(a)} and {len(b)}")
    return [x + y for x, y in zip(a, b)] 