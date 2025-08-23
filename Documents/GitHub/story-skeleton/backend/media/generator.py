"""
Media generation service for scenes
Handles image generation via OpenAI and audio generation via Suno

IMAGE GENERATION BLOCKING:
==========================
To temporarily disable image generation and save API costs during testing:

1. Set environment variable: BLOCK_IMAGE_GENERATION=true
2. Or set environment variable: USE_CPU_STUBS=true (blocks all media generation)

To re-enable image generation:
1. Set BLOCK_IMAGE_GENERATION=false or unset it
2. Ensure USE_CPU_STUBS=false

This block prevents OpenAI API calls while maintaining the same interface.
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import List, Optional
import openai
from .models import MediaAssets, SceneMedia, MediaGenerationRequest
from .config import media_config
from utils.s3 import s3_manager


class MediaGenerator:
    """Media generator for scene assets"""
    
    def __init__(self):
        # Use centralized configuration
        self.config = media_config
        
        # Log the current configuration
        media_config.print_status()
            
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def generate_scene_media(self, request: MediaGenerationRequest) -> SceneMedia:
        """Generate media assets for a scene"""
        print(f"[DEBUG] generate_scene_media: request.generate_images={request.generate_images}")
        print(f"[DEBUG] generate_scene_media: request.generate_audio={request.generate_audio}")
        print(f"[DEBUG] generate_scene_media: request={request}")
        print(f"[DEBUG] generate_scene_media: called for scene_tag={request.scene_tag}, player_id={request.player_id}, image_enabled={self.config.image_generation_enabled}, audio_enabled={self.config.audio_generation_enabled}")
        try:
            media_assets = MediaAssets()
            
            if request.generate_images:
                image_urls = await self._generate_images(request)
                media_assets.images = image_urls
            
            if request.generate_audio:
                audio_urls = await self._generate_audio(request)
                media_assets.audio = audio_urls
            
            return SceneMedia(
                scene_tag=request.scene_tag,
                media=media_assets,
                success=True
            )
            
        except Exception as e:
            print(f"❌ Media generation failed for scene {request.scene_tag}: {e}")
            return SceneMedia(
                scene_tag=request.scene_tag,
                media=MediaAssets(),
                success=False,
                error_message=str(e)
            )
    
    async def _generate_images(self, request: MediaGenerationRequest) -> List[str]:
        """Generate images for a scene"""
        print("[DEBUG] Entered _generate_images")
        
        # Check if image generation is blocked
        if not self.config.image_generation_enabled:
            if self.config.block_image_generation:
                print("🛑 IMAGE GENERATION BLOCKED: Returning placeholder image (BLOCK_IMAGE_GENERATION=true)")
            else:
                print("[DEBUG] use_cpu_stubs is True, returning placeholder image")
            # Return a real HTTP URL for development (ensure this file exists in uploads/ or static/)
            return ["/static/placeholder.jpg"]
            
        print(f"[DEBUG] request.generate_images: {request.generate_images}")
        try:
            # Create prompt from scene text and theme
            prompt = self._create_image_prompt(request.scene_text, request.theme)
            print("[DEBUG] About to call OpenAI image API")
            # Generate image via OpenAI
            response = await self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            print(f"[DEBUG] OpenAI response: {response}")
            
            image_urls = []
            if response.data:
                for i, image in enumerate(response.data):
                    if image.url:
                        # Instead of uploading to S3, just return the OpenAI URL directly
                        image_urls.append(image.url)
            print(f"[DEBUG] Returning image URLs: {image_urls}")
            return image_urls
            
        except Exception as e:
            print(f"❌ Image generation failed: {e}")
            return []
    
    async def _generate_audio(self, request: MediaGenerationRequest) -> List[str]:
        """Generate audio/OST for a scene"""
        if not self.config.audio_generation_enabled:
            # Return stub audio URLs for development
            return [f"s3://stub-audio/{request.scene_tag}/ost.mp3"]
        
        try:
            # Create audio prompt from scene text and theme
            prompt = self._create_audio_prompt(request.scene_text, request.theme)
            
            # TODO: Integrate with Suno API when available
            # For now, return empty list
            print(f"🎵 Audio generation not yet implemented for scene {request.scene_tag}")
            return []
            
        except Exception as e:
            print(f"❌ Audio generation failed: {e}")
            return []
    
    def _create_image_prompt(self, scene_text: str, theme: str) -> str:
        """Create an image generation prompt from scene text and theme"""
        # Extract key visual elements from scene text
        visual_elements = self._extract_visual_elements(scene_text)
        
        prompt = f"""
        Create a cinematic, anime-style illustration for a scene with theme: {theme}
        
        Scene description: {scene_text}
        
        Visual elements: {visual_elements}
        
        Style: High-quality digital art, cinematic lighting, emotional atmosphere, 
        suitable for a hero's journey narrative. Avoid text or words in the image.
        """
        
        return prompt.strip()
    
    def _create_audio_prompt(self, scene_text: str, theme: str) -> str:
        """Create an audio generation prompt from scene text and theme"""
        mood = self._extract_mood(scene_text)
        
        prompt = f"""
        Create atmospheric background music for a scene with theme: {theme}
        
        Scene: {scene_text}
        Mood: {mood}
        
        Style: Cinematic, emotional, suitable for a hero's journey narrative.
        Duration: 30-60 seconds, loopable.
        """
        
        return prompt.strip()
    
    def _extract_visual_elements(self, text: str) -> str:
        """Extract visual elements from scene text"""
        # Simple keyword extraction - could be enhanced with NLP
        visual_keywords = [
            "forest", "castle", "mountain", "river", "cave", "temple", "village",
            "fire", "water", "light", "darkness", "storm", "sunset", "dawn",
            "sword", "shield", "armor", "robe", "crown", "staff", "book",
            "dragon", "knight", "wizard", "princess", "warrior", "sage"
        ]
        
        found_elements = [word for word in visual_keywords if word.lower() in text.lower()]
        return ", ".join(found_elements) if found_elements else "mystical atmosphere"
    
    def _extract_mood(self, text: str) -> str:
        """Extract mood from scene text"""
        mood_keywords = {
            "tension": ["danger", "threat", "enemy", "battle", "fight"],
            "mystery": ["secret", "unknown", "hidden", "mysterious", "enigma"],
            "hope": ["light", "hope", "victory", "triumph", "success"],
            "sadness": ["loss", "grief", "sadness", "tears", "pain"],
            "joy": ["celebration", "joy", "happiness", "laugh", "smile"]
        }
        
        text_lower = text.lower()
        for mood, keywords in mood_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return mood
        
        return "neutral"
    
    async def _download_and_upload_image(self, image_url: str, s3_key: str) -> str:
        """Download image from URL and upload to S3"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Upload to S3
                        s3_url = s3_manager.upload_bytes(
                            image_data, 
                            s3_key, 
                            content_type="image/jpeg"
                        )
                        return s3_url
                    else:
                        raise Exception(f"Failed to download image: {response.status}")
        except ImportError:
            # Fallback for environments without aiohttp
            print("⚠️ aiohttp not available, using stub URL")
            return f"s3://stub-images/{s3_key}"


# Global media generator instance
media_generator = MediaGenerator() 