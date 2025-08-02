"""
SM02: Update soul_maps table structure
"""
from alembic import op
import sqlalchemy as sa
import uuid
from pgvector.sqlalchemy import Vector

revision = 'sm02_update_soulmap_table'
down_revision = 'sm01_init_soulmap'
branch_labels = None
depends_on = None

def upgrade():
    # Drop old table if it exists
    op.drop_table('soul_map', if_exists=True)
    
    # Create new table with updated structure
    op.create_table(
        'soul_maps',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('player_id', sa.String, nullable=False),
        sa.Column('vec', Vector(64), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # Create index on player_id
    op.create_index('ix_soul_maps_player_id', 'soul_maps', ['player_id'])
    
    # Create unique constraint on player_id
    op.create_unique_constraint('uq_soul_maps_player_id', 'soul_maps', ['player_id'])

def downgrade():
    # Drop new table
    op.drop_table('soul_maps')
    
    # Recreate old table structure
    op.create_table(
        'soul_map',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('player_id', sa.String, nullable=False),
        sa.Column('vector', Vector(64), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    ) 