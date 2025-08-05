from sqlalchemy import Column, String, Float, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import JSON
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class NPCState(Base):
    __tablename__ = 'npc_state'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    trust = Column(Float, nullable=False, default=0.0)
    last_seen = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=False, default=dict)

class NPC(Base):
    __tablename__ = 'npc'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    baseline_trust = Column(Float, nullable=False, default=0.0)
    trust = Column(Float, nullable=False, default=0.0)
    # Extended metadata for dynamic NPC generation
    role = Column(String, nullable=True)  # e.g., 'Mentor', 'Rival', 'Companion'
    archetype = Column(String, nullable=True)  # e.g., 'Sage', 'Warrior', 'Trickster'
    personality_traits = Column(JSON, nullable=True, default=list)  # List of personality traits
    narrative_hooks = Column(JSON, nullable=True, default=list)  # List of story hooks
    relationship_to_player = Column(String, nullable=True)  # How NPC relates to player
    motivation = Column(String, nullable=True)  # What drives the NPC
    secrets = Column(JSON, nullable=True, default=list)  # List of secrets
    generated = Column(String, nullable=True)  # Flag to indicate if dynamically generated 