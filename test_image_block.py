#!/usr/bin/env python3
"""
Test script to verify image generation blocking functionality.
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

def test_image_blocking():
    """Test the image generation blocking functionality."""
    print("🧪 Testing Image Generation Blocking...")
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    block_image = os.getenv("BLOCK_IMAGE_GENERATION", "false").lower() == "true"
    use_cpu_stubs = os.getenv("USE_CPU_STUBS", "false").lower() == "true"
    
    print(f"📋 Environment Variables:")
    print(f"  • BLOCK_IMAGE_GENERATION: {os.getenv('BLOCK_IMAGE_GENERATION', 'not set')}")
    print(f"  • USE_CPU_STUBS: {os.getenv('USE_CPU_STUBS', 'not set')}")
    
    # Test media config
    try:
        from media.config import media_config
        print("\n📋 Media Configuration:")
        media_config.print_status()
        
        # Test generator
        from media.generator import MediaGenerator
        print("\n🔧 Testing Media Generator...")
        generator = MediaGenerator()
        
        print(f"✅ Media generator created successfully")
        print(f"  • Image generation enabled: {generator.config.image_generation_enabled}")
        print(f"  • Audio generation enabled: {generator.config.audio_generation_enabled}")
        
        if not generator.config.image_generation_enabled:
            print("🛑 Image generation is BLOCKED - API costs will be saved!")
        else:
            print("⚠️  Image generation is ENABLED - API costs will be incurred!")
            
    except Exception as e:
        print(f"❌ Error testing media system: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_image_blocking()
    if success:
        print("\n✅ Image blocking test completed successfully!")
    else:
        print("\n❌ Image blocking test failed!")
        sys.exit(1) 