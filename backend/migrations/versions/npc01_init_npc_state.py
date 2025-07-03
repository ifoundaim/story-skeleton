"""
NPC01: Initial npc_state table
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = 'npc01_init_npc_state'
down_revision = 'sm01_init_soulmap'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'npc_state',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('player_id', sa.String, nullable=False, index=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('trust', sa.Float, nullable=False, default=0.0),
        sa.Column('last_seen', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta', sa.dialects.postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index('ix_npc_state_player_id', 'npc_state', ['player_id'])

def downgrade():
    op.drop_index('ix_npc_state_player_id', table_name='npc_state')
    op.drop_table('npc_state') 