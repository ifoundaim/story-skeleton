"""
Pydantic models for media assets and scene media responses
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MediaAssets(BaseModel):
    """Media assets for a scene"""
    images: List[str] = Field(default_factory=list, description="S3 URLs for scene images")
    audio: List[str] = Field(default_factory=list, description="S3 URLs for scene audio/OST")


class SceneMedia(BaseModel):
    """Media response for scene generation"""
    scene_tag: str
    media: MediaAssets = Field(default_factory=MediaAssets)
    success: bool = True
    error_message: Optional[str] = None


class MediaGenerationRequest(BaseModel):
    """Request for media generation"""
    scene_tag: str
    scene_text: str
    theme: str
    player_id: str
    generate_images: bool = True
    generate_audio: bool = True 