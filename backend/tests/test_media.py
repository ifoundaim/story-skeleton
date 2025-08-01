"""
Tests for Narrative Media Layer v1 (SPR-MEDIA01)
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from backend.media.models import MediaAssets, SceneMedia, MediaGenerationRequest
from backend.media.generator import MediaGenerator
from purpose_agents.codex_router import CodexRouter, TaskStatus


class TestMediaModels:
    """Test media Pydantic models"""
    
    def test_media_assets_defaults(self):
        """Test MediaAssets with default values"""
        assets = MediaAssets()
        assert assets.images == []
        assert assets.audio == []
    
    def test_media_assets_with_data(self):
        """Test MediaAssets with provided data"""
        assets = MediaAssets(
            images=["s3://bucket/image1.jpg", "s3://bucket/image2.jpg"],
            audio=["s3://bucket/ost1.mp3"]
        )
        assert len(assets.images) == 2
        assert len(assets.audio) == 1
        assert "image1.jpg" in assets.images[0]
    
    def test_scene_media_success(self):
        """Test SceneMedia with successful generation"""
        media = SceneMedia(
            scene_tag="test_scene",
            media=MediaAssets(images=["s3://test.jpg"]),
            success=True
        )
        assert media.scene_tag == "test_scene"
        assert media.success is True
        assert media.error_message is None
        assert len(media.media.images) == 1
    
    def test_scene_media_failure(self):
        """Test SceneMedia with failed generation"""
        media = SceneMedia(
            scene_tag="test_scene",
            media=MediaAssets(),
            success=False,
            error_message="API error"
        )
        assert media.success is False
        assert media.error_message == "API error"


class TestMediaGenerator:
    """Test MediaGenerator functionality"""
    
    @pytest.fixture
    def generator(self):
        """Create a MediaGenerator instance"""
        return MediaGenerator()
    
    @pytest.fixture
    def request_data(self):
        """Sample media generation request"""
        return MediaGenerationRequest(
            scene_tag="test_scene",
            scene_text="A brave knight enters a dark forest",
            theme="hero's journey",
            player_id="test_player"
        )
    
    def test_extract_visual_elements(self, generator):
        """Test visual element extraction"""
        text = "The knight enters a dark forest with a sword"
        elements = generator._extract_visual_elements(text)
        assert "forest" in elements
        assert "sword" in elements
    
    def test_extract_mood(self, generator):
        """Test mood extraction"""
        text = "The knight faces a dangerous enemy in battle"
        mood = generator._extract_mood(text)
        assert mood == "tension"
    
    def test_create_image_prompt(self, generator):
        """Test image prompt creation"""
        prompt = generator._create_image_prompt(
            "A knight in a forest",
            "hero's journey"
        )
        assert "knight" in prompt
        assert "forest" in prompt
        assert "hero's journey" in prompt
    
    def test_create_audio_prompt(self, generator):
        """Test audio prompt creation"""
        prompt = generator._create_audio_prompt(
            "A knight in a forest",
            "hero's journey"
        )
        assert "knight" in prompt
        assert "hero's journey" in prompt
    
    @patch.dict(os.environ, {"USE_CPU_STUBS": "true"})
    def test_generate_images_cpu_stubs(self, generator, request_data):
        """Test image generation with CPU stubs"""
        async def test():
            urls = await generator._generate_images(request_data)
            assert len(urls) == 1
            # Accept either the old stub or the new placeholder
            assert (
                "stub-images" in urls[0] or urls[0] == "/static/placeholder.jpg"
            )
        
        asyncio.run(test())
    
    @patch.dict(os.environ, {"USE_CPU_STUBS": "true"})
    def test_generate_audio_cpu_stubs(self, generator, request_data):
        """Test audio generation with CPU stubs"""
        async def test():
            urls = await generator._generate_audio(request_data)
            assert len(urls) == 1
            assert "stub-audio" in urls[0]
        
        asyncio.run(test())
    
    @patch.dict(os.environ, {"USE_CPU_STUBS": "true"})
    def test_generate_scene_media_success(self, generator, request_data):
        """Test successful scene media generation"""
        async def test():
            result = await generator.generate_scene_media(request_data)
            assert result.success is True
            assert result.scene_tag == "test_scene"
            assert len(result.media.images) == 1
            assert len(result.media.audio) == 1
        
        asyncio.run(test())
    
    @patch.dict(os.environ, {"USE_CPU_STUBS": "false"})
    @patch('backend.media.generator.openai.AsyncOpenAI')
    def test_generate_images_openai_error(self, mock_openai, generator, request_data):
        """Test image generation with OpenAI error"""
        mock_client = AsyncMock()
        mock_client.images.generate.side_effect = Exception("API error")
        mock_openai.return_value = mock_client

        async def test():
            # Ensure USE_CPU_STUBS is false for this test
            os.environ["USE_CPU_STUBS"] = "false"
            # Re-instantiate generator to pick up env var
            gen = MediaGenerator()
            urls = await gen._generate_images(request_data)
            assert urls == []

        asyncio.run(test())


class TestCodexRouter:
    """Test CodexRouter functionality"""
    
    @pytest.fixture
    def router(self):
        """Create a CodexRouter instance"""
        return CodexRouter()
    
    def test_enqueue_media_generation(self, router):
        """Test enqueuing media generation tasks"""
        async def test():
            task_id = await router.enqueue_media_generation(
                scene_tag="test_scene",
                scene_text="Test scene",
                theme="test theme",
                player_id="test_player"
            )
            assert task_id is not None
            assert task_id in router.tasks
            assert router.tasks[task_id].status == TaskStatus.PENDING
        
        asyncio.run(test())
    
    def test_get_task_status(self, router):
        """Test getting task status"""
        # Add a test task
        task = router.tasks["test_task"] = Mock()
        task.status = TaskStatus.COMPLETED
        
        status = router.get_task_status("test_task")
        assert status == TaskStatus.COMPLETED
        
        # Test non-existent task
        status = router.get_task_status("non_existent")
        assert status is None
    
    def test_should_generate_media(self, router):
        """Test media generation decision logic"""
        # No media - should generate both
        generate_images, generate_audio = router.should_generate_media(None)
        assert generate_images is True
        assert generate_audio is True
        
        # Has images, no audio
        media = MediaAssets(images=["s3://test.jpg"], audio=[])
        generate_images, generate_audio = router.should_generate_media(media)
        assert generate_images is False
        assert generate_audio is True
        
        # Has both
        media = MediaAssets(images=["s3://test.jpg"], audio=["s3://test.mp3"])
        generate_images, generate_audio = router.should_generate_media(media)
        assert generate_images is False
        assert generate_audio is False


class TestMediaIntegration:
    """Integration tests for media layer"""
    
    @patch.dict(os.environ, {"USE_CPU_STUBS": "true"})
    def test_media_generation_workflow(self):
        """Test complete media generation workflow"""
        async def test():
            # Create components
            generator = MediaGenerator()
            router = CodexRouter()
            
            # Create request
            request = MediaGenerationRequest(
                scene_tag="integration_test",
                scene_text="Integration test scene",
                theme="test theme",
                player_id="test_player"
            )
            
            # Enqueue task
            task_id = await router.enqueue_media_generation(
                scene_tag=request.scene_tag,
                scene_text=request.scene_text,
                theme=request.theme,
                player_id=request.player_id
            )
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Check result
            result = router.get_task_result(task_id)
            assert result is not None
            assert result.success is True
            assert result.scene_tag == "integration_test"
        
        asyncio.run(test())


if __name__ == "__main__":
    pytest.main([__file__]) 