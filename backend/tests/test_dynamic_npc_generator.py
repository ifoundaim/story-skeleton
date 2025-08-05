"""
Tests for the Dynamic NPC Seed Generator & Profile Factory (SPR-NPC06)
"""

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from sqlalchemy.orm import Session

from npc.dynamic_generator import DynamicNPCGenerator, generate_story_npcs
from npc.models import NPC
from db import SessionLocal


class TestDynamicNPCGenerator:
    """Test the DynamicNPCGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = DynamicNPCGenerator()
        self.db = SessionLocal()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.db.close()
    
    def test_init_without_openai(self):
        """Test initialization without OpenAI API key."""
        with patch.dict('os.environ', {}, clear=True):
            generator = DynamicNPCGenerator()
            assert generator.client is None
    
    def test_init_with_openai(self):
        """Test initialization with OpenAI API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('openai.AsyncOpenAI') as mock_openai:
                generator = DynamicNPCGenerator()
                mock_openai.assert_called_once_with(api_key='test-key')
    
    def test_get_dominant_traits(self):
        """Test extraction of dominant traits from soul map."""
        soul_map = {
            "COURAGE": 0.8,
            "WISDOM": -0.3,
            "FEAR": 0.1,
            "COMPASSION": 0.9,
            "PRIDE": -0.7
        }
        
        dominant_traits = self.generator._get_dominant_traits(soul_map, top_k=3)
        
        # Should return traits sorted by absolute value
        expected = ["PRIDE", "COMPASSION", "COURAGE"]
        assert dominant_traits == expected
    
    def test_build_npc_generation_prompt(self):
        """Test prompt building for NPC generation."""
        player_name = "TestPlayer"
        player_archetype = "Hero"
        soul_map = {"COURAGE": 0.8, "WISDOM": 0.6}
        story_theme = "Adventure"
        
        prompt = self.generator._build_npc_generation_prompt(
            player_name, player_archetype, soul_map, story_theme, 3
        )
        
        assert "TestPlayer" in prompt
        assert "Hero" in prompt
        assert "Adventure" in prompt
        assert "COURAGE" in prompt
        assert "WISDOM" in prompt
        assert "Generate 3 unique NPC profiles" in prompt
    
    def test_generate_fallback_npcs(self):
        """Test fallback NPC generation when LLM is not available."""
        npcs = self.generator._generate_fallback_npcs("Hero", "Adventure", 2)
        
        assert len(npcs) == 2
        assert all(isinstance(npc, dict) for npc in npcs)
        assert all("id" in npc for npc in npcs)
        assert all("full_name" in npc for npc in npcs)
        assert all("role" in npc for npc in npcs)
        assert all("archetype" in npc for npc in npcs)
        assert all("baseline_trust" in npc for npc in npcs)
    
    def test_strip_code_fences(self):
        """Test removal of code fence markers from LLM responses."""
        # Test with ```json
        text = "```json\n{\"test\": \"value\"}\n```"
        cleaned = self.generator._strip_code_fences(text)
        assert cleaned == "{\"test\": \"value\"}"
        
        # Test with just ```
        text = "```\n{\"test\": \"value\"}\n```"
        cleaned = self.generator._strip_code_fences(text)
        assert cleaned == "{\"test\": \"value\"}"
        
        # Test without fences
        text = "{\"test\": \"value\"}"
        cleaned = self.generator._strip_code_fences(text)
        assert cleaned == "{\"test\": \"value\"}"
    
    def test_create_npc_from_data(self):
        """Test creating NPC database record from generated data."""
        npc_info = {
            "id": "test_npc_001",
            "full_name": "Test NPC",
            "role": "Mentor",
            "archetype": "Sage",
            "baseline_trust": 0.7,
            "personality_traits": ["Wise", "Patient"],
            "narrative_hooks": ["Knows ancient secrets"],
            "relationship_to_player": "Guiding mentor",
            "motivation": "To teach",
            "secrets": ["Has hidden knowledge"]
        }
        
        npc = self.generator._create_npc_from_data(npc_info, self.db)
        
        assert isinstance(npc, NPC)
        assert npc.full_name == "Test NPC"
        assert npc.role == "Mentor"
        assert npc.archetype == "Sage"
        assert npc.baseline_trust == 0.7
        assert npc.trust == 0.7
        assert npc.personality_traits == ["Wise", "Patient"]
        assert npc.narrative_hooks == ["Knows ancient secrets"]
        assert npc.relationship_to_player == "Guiding mentor"
        assert npc.motivation == "To teach"
        assert npc.secrets == ["Has hidden knowledge"]
        assert npc.generated == "true"
    
    @pytest.mark.asyncio
    async def test_generate_npc_data_with_openai(self):
        """Test NPC data generation with OpenAI."""
        mock_response = AsyncMock()
        mock_response.choices[0].message.content = '''
        {
            "npcs": [
                {
                    "id": "test_npc_001",
                    "full_name": "Test NPC",
                    "role": "Mentor",
                    "archetype": "Sage",
                    "baseline_trust": 0.7,
                    "personality_traits": ["Wise", "Patient"],
                    "narrative_hooks": ["Knows ancient secrets"],
                    "relationship_to_player": "Guiding mentor",
                    "motivation": "To teach",
                    "secrets": ["Has hidden knowledge"]
                }
            ]
        }
        '''
        
        with patch.object(self.generator, 'client', AsyncMock()) as mock_client:
            mock_client.chat.completions.create.return_value = mock_response
            
            npc_data = await self.generator._generate_npc_data(
                "TestPlayer", "Hero", {"COURAGE": 0.8}, "Adventure", 1
            )
            
            assert len(npc_data) == 1
            assert npc_data[0]["id"] == "test_npc_001"
            assert npc_data[0]["full_name"] == "Test NPC"
    
    @pytest.mark.asyncio
    async def test_generate_npc_data_fallback(self):
        """Test NPC data generation falls back when OpenAI fails."""
        with patch.object(self.generator, 'client', None):
            npc_data = await self.generator._generate_npc_data(
                "TestPlayer", "Hero", {"COURAGE": 0.8}, "Adventure", 2
            )
            
            assert len(npc_data) == 2
            assert all(isinstance(npc, dict) for npc in npc_data)
    
    @pytest.mark.asyncio
    async def test_generate_npc_profiles(self):
        """Test full NPC profile generation workflow."""
        # Mock soul map data
        with patch('npc.dynamic_generator.get_soulmap_dict') as mock_get_soulmap:
            mock_get_soulmap.return_value = {"COURAGE": 0.8, "WISDOM": 0.6}
            
            # Mock NPC data generation
            with patch.object(self.generator, '_generate_npc_data') as mock_generate:
                mock_generate.return_value = [{
                    "id": "test_npc_001",
                    "full_name": "Test NPC",
                    "role": "Mentor",
                    "archetype": "Sage",
                    "baseline_trust": 0.7,
                    "personality_traits": ["Wise"],
                    "narrative_hooks": ["Knows secrets"],
                    "relationship_to_player": "Mentor",
                    "motivation": "To teach",
                    "secrets": ["Hidden knowledge"]
                }]
                
                npcs = await self.generator.generate_npc_profiles(
                    "test_player",
                    "TestPlayer",
                    "Hero",
                    "Adventure",
                    1,
                    self.db
                )
                
                assert len(npcs) == 1
                assert isinstance(npcs[0], NPC)
                assert npcs[0].full_name == "Test NPC"


@pytest.mark.asyncio
async def test_generate_story_npcs():
    """Test the convenience function for generating story NPCs."""
    with patch('npc.dynamic_generator.npc_generator.generate_npc_profiles') as mock_generate:
        mock_npcs = [NPC(id=uuid.uuid4(), full_name="Test NPC")]
        mock_generate.return_value = mock_npcs
        
        result = await generate_story_npcs(
            "test_player",
            "TestPlayer",
            "Hero",
            "Adventure",
            1
        )
        
        assert result == mock_npcs
        mock_generate.assert_called_once_with(
            "test_player", "TestPlayer", "Hero", "Adventure", 1
        ) 