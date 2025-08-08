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
    role = Column(String, nullable=True)  # Mentor, Companion, Rival, etc.
    archetype = Column(String, nullable=True)  # Sage, Warrior, Archer, etc.
    personality_traits = Column(JSON, nullable=True, default=list)  # List of personality traits
    narrative_hooks = Column(JSON, nullable=True, default=list)  # List of narrative hooks
    motivation = Column(String, nullable=True)  # NPC's motivation
    relationship_to_player = Column(String, nullable=True)  # Relationship description 