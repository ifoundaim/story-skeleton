from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import text
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()

class SoulMap(Base):
    __tablename__ = 'soul_map'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(String, nullable=False, index=True)
    vector = Column(Vector(64), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False) 