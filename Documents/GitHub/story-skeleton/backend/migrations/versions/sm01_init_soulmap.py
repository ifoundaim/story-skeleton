"""
SM01: Initial soul_map table
"""
from alembic import op
import sqlalchemy as sa
import uuid
from pgvector.sqlalchemy import Vector

revision = 'sm01_init_soulmap'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Ensure pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'soul_map',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('player_id', sa.String, nullable=False),
        sa.Column('vector', Vector(64), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

def downgrade():
    op.drop_table('soul_map') 