"""
Unit tests for onboard flow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from datetime import datetime

from npc.service import onboard_npc
from npc.models import NPCState


class TestOnboardFlow:
    
    def setup_method(self):
        """Set up test fixtures"""
        self.player_id = "test_player_123"
        self.npc_id = str(uuid.uuid4())
        self.mock_db = Mock()
        
        # Mock NPC state
        self.mock_npc = Mock(spec=NPCState)
        self.mock_npc.id = uuid.UUID(self.npc_id)
        self.mock_npc.name = "Test NPC"
        self.mock_npc.trust = 0.65
        self.mock_npc.meta = {"is_companion": False}
    
    def test_onboard_npc_creates_companion_status(self):
        """Test that onboard_npc marks NPC as companion"""
        # Arrange
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        assert result.meta["is_companion"] is True
        assert "onboarded_at" in result.meta
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(result)
    
    def test_onboard_npc_boosts_trust(self):
        """Test that onboard_npc boosts trust by 0.05"""
        # Arrange
        initial_trust = 0.65
        self.mock_npc.trust = initial_trust
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        expected_trust = min(initial_trust + 0.05, 1.0)
        assert result.trust == expected_trust
    
    def test_onboard_npc_clamps_trust_at_maximum(self):
        """Test that onboard_npc clamps trust at 1.0 maximum"""
        # Arrange
        self.mock_npc.trust = 0.98  # Close to maximum
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        assert result.trust == 1.0  # Clamped at maximum
    
    def test_onboard_npc_creates_new_npc_if_not_exists(self):
        """Test that onboard_npc creates new NPC if it doesn't exist"""
        # Arrange
        with patch('npc.service.get_npc_by_id', return_value=None):
            with patch('npc.service.create_default_npc') as mock_create:
                mock_create.return_value = self.mock_npc
                
                # Act
                result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        mock_create.assert_called_once_with(
            self.player_id, 
            self.npc_id, 
            f"Companion-{self.npc_id[:8]}", 
            self.mock_db
        )
    
    def test_onboard_npc_records_timestamp(self):
        """Test that onboard_npc records onboarding timestamp"""
        # Arrange
        mock_timestamp = "2024-01-01T12:00:00"
        self.mock_db.query.return_value.scalar.return_value.isoformat.return_value = mock_timestamp
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        assert result.meta["onboarded_at"] == mock_timestamp
    
    def test_onboard_npc_handles_uuid_strings(self):
        """Test that onboard_npc handles UUID strings correctly"""
        # Arrange
        uuid_string = str(uuid.uuid4())
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, uuid_string, self.mock_db)
        
        # Assert
        assert result.meta["is_companion"] is True
    
    def test_onboard_npc_handles_uuid_objects(self):
        """Test that onboard_npc handles UUID objects correctly"""
        # Arrange
        uuid_obj = uuid.uuid4()
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, uuid_obj, self.mock_db)
        
        # Assert
        assert result.meta["is_companion"] is True
    
    def test_onboard_npc_preserves_existing_meta(self):
        """Test that onboard_npc preserves existing metadata"""
        # Arrange
        existing_meta = {"personality": "brave", "background": "warrior"}
        self.mock_npc.meta = existing_meta.copy()
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act
            result = onboard_npc(self.player_id, self.npc_id, self.mock_db)
        
        # Assert
        assert result.meta["personality"] == "brave"
        assert result.meta["background"] == "warrior"
        assert result.meta["is_companion"] is True
        assert "onboarded_at" in result.meta
    
    def test_onboard_npc_handles_database_errors_gracefully(self):
        """Test that onboard_npc handles database errors gracefully"""
        # Arrange
        self.mock_db.commit.side_effect = Exception("Database error")
        
        with patch('npc.service.get_npc_by_id', return_value=self.mock_npc):
            # Act & Assert
            with pytest.raises(Exception, match="Database error"):
                onboard_npc(self.player_id, self.npc_id, self.mock_db)
    
    def test_onboard_npc_generates_appropriate_default_name(self):
        """Test that onboard_npc generates appropriate default name for new NPCs"""
        # Arrange
        test_npc_id = "12345678-1234-1234-1234-123456789abc"
        expected_name = "Companion-12345678"
        
        with patch('npc.service.get_npc_by_id', return_value=None):
            with patch('npc.service.create_default_npc') as mock_create:
                mock_create.return_value = self.mock_npc
                
                # Act
                onboard_npc(self.player_id, test_npc_id, self.mock_db)
        
        # Assert
        mock_create.assert_called_once_with(
            self.player_id, 
            test_npc_id, 
            expected_name, 
            self.mock_db
        ) 