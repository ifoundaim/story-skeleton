import pytest
from .recap_builder import build_memory

def test_build_memory_basic():
    story = {
        "scene1": {
            "text": "Kai entered the garden of twilight.",
            "npc_text": "Liora greeted him warmly."
        },
        "scene2": {
            "text": "He passed through the broken temple.",
            "npc_text": "A wounded NPC, Liora, began to trust him."
        },
        "scene3": {
            "text": "Kai faced the river of memory.",
            "npc_text": "He felt awe and grief."
        }
    }
    history = ["scene1", "scene2", "scene3"]
    recap = build_memory("kai-22", story, history)
    assert "Kai entered the garden of twilight." in recap
    assert "Liora greeted him warmly." in recap
    assert "He passed through the broken temple." in recap
    assert "A wounded NPC, Liora, began to trust him." in recap
    assert "Kai faced the river of memory." in recap
    assert "He felt awe and grief." in recap
    # Should be under 300 words
    assert len(recap.split()) <= 300 