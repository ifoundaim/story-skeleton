# backend/story/__init__.py
"""
Story generation and management package.
"""

from .choice_generator import Choice, make_contextual_choice, generate_template_choice, should_enable_free_text
from .telemetry import log_scene_decision, log_choice_generated, log_free_text

__all__ = [
    'Choice',
    'make_contextual_choice', 
    'generate_template_choice',
    'should_enable_free_text',
    'log_scene_decision',
    'log_choice_generated',
    'log_free_text'
]

