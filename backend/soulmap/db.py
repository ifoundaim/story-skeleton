from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector
import uuid

# Use the shared database configuration
from backend.db import engine, SessionLocal

Base = declarative_base()

class SoulMap(Base):
    __tablename__ = 'soul_maps'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(String, nullable=False, index=True, unique=True)
    vec = Column(Vector(64), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<SoulMap(player_id='{self.player_id}', updated_at='{self.updated_at}')>"

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine) 