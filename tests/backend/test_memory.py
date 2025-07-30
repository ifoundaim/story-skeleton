"""Tests for the memory recap system."""

import json
import os
import tempfile
from unittest.mock import patch
import pytest

from codex.memory.recap_builder import build_memory, update_memory, get_memory, _load_memory, _save_memory


class TestMemoryRecapBuilder:
    """Test the memory recap builder functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_story = {
            "intro_001": {
                "text": "Kai entered the broken temple, feeling a sense of awe and mystery.",
                "npc_text": "The wounded Liora looked up with hope in her eyes.",
                "choices": [
                    {"text": "Help Liora", "tag": "help_choice"},
                    {"text": "Leave her", "tag": "leave_choice"}
                ],
                "emotion_delta": [0.2, 0.1, -0.1, 0.3]
            },
            "help_001": {
                "text": "Kai decided to help Liora, bandaging her wounds carefully.",
                "npc_text": "Thank you, brave one. I am Liora, guardian of this temple.",
                "choices": [
                    {"text": "Ask about the temple", "tag": "ask_temple"},
                    {"text": "Focus on healing", "tag": "heal_focus"}
                ],
                "emotion_delta": [0.4, 0.2, 0.1, 0.5]
            },
            "temple_001": {
                "text": "The temple revealed ancient secrets as Kai explored its depths.",
                "npc_text": "The wise Elder Thorne appeared from the shadows.",
                "choices": [
                    {"text": "Listen to Elder Thorne", "tag": "listen_elder"},
                    {"text": "Continue exploring", "tag": "explore_more"}
                ],
                "emotion_delta": [0.1, 0.3, 0.2, 0.1]
            },
            "final_001": {
                "text": "Kai faced the final challenge with courage and determination.",
                "npc_text": "You have proven yourself worthy, young one.",
                "choices": [
                    {"text": "Accept the challenge", "tag": "accept"},
                    {"text": "Seek another path", "tag": "alternative"}
                ],
                "emotion_delta": [0.5, 0.4, 0.3, 0.6]
            }
        }
        
        self.test_history = ["intro_001", "help_001", "temple_001", "final_001"]
        self.player_id = "kai-22"
    
    def test_build_memory_basic_narrative(self):
        """Test that build_memory creates a coherent narrative."""
        recap = build_memory(self.player_id, self.test_story, self.test_history)
        
        # Should include player name
        assert "Kai" in recap
        
        # Should include NPC names
        assert "Liora" in recap
        assert "Elder Thorne" in recap
        
        # Should be a reasonable length (not too short, not too long)
        words = recap.split()
        assert 50 <= len(words) <= 350  # Allow some flexibility
        
        # Should read like a narrative
        assert recap.endswith(('.', '!', '?'))
    
    def test_build_memory_emotion_trends(self):
        """Test that emotion trends are extracted and included."""
        recap = build_memory(self.player_id, self.test_story, self.test_history)
        
        # Should mention emotions due to significant emotion deltas
        assert any(word in recap.lower() for word in ["emotions", "mood", "felt"])
    
    def test_build_memory_npc_interactions(self):
        """Test that NPC interactions are properly extracted."""
        recap = build_memory(self.player_id, self.test_story, self.test_history)
        
        # Should mention NPC encounters
        assert any(word in recap.lower() for word in ["encountered", "met"])
        
        # Should include specific NPC names
        assert "Liora" in recap
        assert "Elder Thorne" in recap
    
    def test_build_memory_choice_patterns(self):
        """Test that choice patterns are detected."""
        recap = build_memory(self.player_id, self.test_story, self.test_history)
        
        # Should mention approach based on choices
        assert any(word in recap.lower() for word in ["help", "approach"])
    
    def test_build_memory_empty_history(self):
        """Test behavior with empty history."""
        recap = build_memory(self.player_id, self.test_story, [])
        assert "not yet begun" in recap or "remains unclear" in recap
    
    def test_build_memory_word_limit(self):
        """Test that recap respects word limit."""
        # Create a very long story
        long_story = {}
        for i in range(10):
            long_story[f"scene_{i}"] = {
                "text": "This is a very long scene description that goes on and on with many words to test the word limit functionality of the memory recap builder. " * 5,
                "npc_text": "The NPC says many things in this very long dialogue that should be truncated appropriately. " * 3,
                "choices": [{"text": "Choice 1", "tag": "choice1"}],
                "emotion_delta": [0.1, 0.1, 0.1, 0.1]
            }
        
        long_history = [f"scene_{i}" for i in range(10)]
        recap = build_memory(self.player_id, long_story, long_history)
        
        words = recap.split()
        assert len(words) <= 350  # Should be truncated
    
    def test_build_memory_sentence_boundaries(self):
        """Test that truncation respects sentence boundaries."""
        recap = build_memory(self.player_id, self.test_story, self.test_history)
        
        # Should end with proper punctuation
        assert recap.endswith(('.', '!', '?'))
        
        # If truncated, should end with "..."
        if len(recap.split()) >= 300:
            assert recap.endswith('...')
    
    @patch('codex.memory.recap_builder.MEMORY_PATH')
    def test_update_memory_persistence(self, mock_path):
        """Test that update_memory persists data correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            mock_path.__str__ = lambda: f.name
        
        try:
            # Test initial update
            recap = update_memory(self.player_id, self.test_story, self.test_history)
            assert recap is not None
            
            # Verify data was saved
            saved_memory = _load_memory()
            assert self.player_id in saved_memory
            assert "recap" in saved_memory[self.player_id]
            assert "last_updated" in saved_memory[self.player_id]
            
            # Test retrieval
            retrieved_recap = get_memory(self.player_id)
            assert retrieved_recap == recap
            
        finally:
            # Cleanup
            if os.path.exists(f.name):
                os.unlink(f.name)
    
    def test_get_memory_nonexistent_player(self):
        """Test get_memory with non-existent player."""
        recap = get_memory("nonexistent-player")
        assert recap is None
    
    def test_load_memory_file_not_found(self):
        """Test _load_memory when file doesn't exist."""
        with patch('codex.memory.recap_builder.MEMORY_PATH', '/nonexistent/path/memory.json'):
            memory = _load_memory()
            assert memory == {}
    
    def test_load_memory_invalid_json(self):
        """Test _load_memory with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("invalid json content")
            f.flush()
            
            with patch('codex.memory.recap_builder.MEMORY_PATH', f.name):
                memory = _load_memory()
                assert memory == {}
        
        os.unlink(f.name)
    
    def test_save_memory_creates_directory(self):
        """Test that _save_memory creates directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "nonexistent", "memory.json")
            
            with patch('codex.memory.recap_builder.MEMORY_PATH', test_path):
                test_data = {"test": "data"}
                _save_memory(test_data)
                
                # Verify file was created
                assert os.path.exists(test_path)
                
                # Verify content
                with open(test_path, 'r') as f:
                    loaded_data = json.load(f)
                    assert loaded_data == test_data


if __name__ == "__main__":
    pytest.main([__file__]) 