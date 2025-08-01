"""
Media generation configuration and blocking controls.

This module provides centralized configuration for media generation,
including easy-to-use blocking mechanisms to prevent API costs during testing.

USAGE:
======
To block image generation during testing:
    export BLOCK_IMAGE_GENERATION=true

To block all media generation:
    export USE_CPU_STUBS=true

To re-enable:
    export BLOCK_IMAGE_GENERATION=false
    export USE_CPU_STUBS=false

CONFIGURATION:
==============
- BLOCK_IMAGE_GENERATION: Blocks only image generation (OpenAI API calls)
- USE_CPU_STUBS: Blocks all media generation (images + audio)
- OPENAI_API_KEY: Required for image generation when not blocked
"""

import os
from typing import Dict, Any


class MediaConfig:
    """Configuration for media generation services."""
    
    def __init__(self):
        self.use_cpu_stubs = os.getenv("USE_CPU_STUBS", "false").lower() == "true"
        self.block_image_generation = os.getenv("BLOCK_IMAGE_GENERATION", "false").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        
    @property
    def image_generation_enabled(self) -> bool:
        """Check if image generation is enabled."""
        return not (self.use_cpu_stubs or self.block_image_generation)
    
    @property
    def audio_generation_enabled(self) -> bool:
        """Check if audio generation is enabled."""
        return not self.use_cpu_stubs
    
    def get_status(self) -> Dict[str, Any]:
        """Get current configuration status."""
        return {
            "use_cpu_stubs": self.use_cpu_stubs,
            "block_image_generation": self.block_image_generation,
            "image_generation_enabled": self.image_generation_enabled,
            "audio_generation_enabled": self.audio_generation_enabled,
            "openai_api_key_configured": bool(self.openai_api_key),
        }
    
    def print_status(self) -> None:
        """Print current configuration status."""
        status = self.get_status()
        
        print("📋 Media Generation Configuration:")
        print(f"  • CPU Stubs Mode: {'🛑 BLOCKED' if status['use_cpu_stubs'] else '✅ ENABLED'}")
        print(f"  • Image Generation: {'🛑 BLOCKED' if not status['image_generation_enabled'] else '✅ ENABLED'}")
        print(f"  • Audio Generation: {'🛑 BLOCKED' if not status['audio_generation_enabled'] else '✅ ENABLED'}")
        print(f"  • OpenAI API Key: {'✅ CONFIGURED' if status['openai_api_key_configured'] else '❌ MISSING'}")
        
        if not status['image_generation_enabled']:
            if status['use_cpu_stubs']:
                print("  📝 To enable image generation: Set USE_CPU_STUBS=false")
            else:
                print("  📝 To enable image generation: Set BLOCK_IMAGE_GENERATION=false")
        
        if not status['audio_generation_enabled']:
            print("  📝 To enable audio generation: Set USE_CPU_STUBS=false")


# Global configuration instance
media_config = MediaConfig() 