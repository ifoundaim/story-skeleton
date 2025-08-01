"""
Narrative Media Layer v1 (SPR-MEDIA01)

Handles generation and management of scene media assets including:
- Images via OpenAI Image API
- Audio/OST via Suno API
- S3 storage and retrieval
"""

from .generator import MediaGenerator
from .models import MediaAssets, SceneMedia

__all__ = ["MediaGenerator", "MediaAssets", "SceneMedia"] 