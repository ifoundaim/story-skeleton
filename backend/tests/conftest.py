import os
import pytest
from sqlalchemy import text

# Set testing environment before any imports
os.environ["TESTING"] = "1"

# Patch database configuration BEFORE importing any modules that use it
import backend.db
backend.db.SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
backend.db.engine = backend.db.create_engine(backend.db.SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
backend.db.SessionLocal = backend.db.sessionmaker(autocommit=False, autoflush=False, bind=backend.db.engine)

# Import and patch routers
import backend.npc.router as npc_router
import backend.npc.service as npc_service
import backend.soulmap.router as soulmap_router

# Create tables in the test database
from backend.npc.models import Base as NPCBase
from backend.soulmap.db import Base as SoulMapBase
NPCBase.metadata.create_all(bind=backend.db.engine)
SoulMapBase.metadata.create_all(bind=backend.db.engine)

# Patch SessionLocal in services
npc_service.SessionLocal = backend.db.SessionLocal
soulmap_router.SessionLocal = backend.db.SessionLocal

def _get_test_db():
    db = backend.db.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Patch get_db functions
npc_router.get_db = _get_test_db
soulmap_router.get_db = _get_test_db

@pytest.fixture(scope="function")
def db():
    db = backend.db.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function", autouse=True)
def clean_db():
    """Clean the database before each test"""
    # Delete all data from tables
    with backend.db.engine.connect() as conn:
        conn.execute(text("DELETE FROM npc_state"))
        conn.execute(text("DELETE FROM npc"))  # Add cleanup for new NPC table
        conn.execute(text("DELETE FROM soul_maps"))
        conn.commit()

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c
