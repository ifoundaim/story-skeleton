"""
NPC01: Initial npc_state table
"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = 'npc01_init_npc_state'
down_revision = 'sm01_init_soulmap'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'npc_state',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('player_id', sa.String, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('trust', sa.Float, nullable=False, default=0.0),
        sa.Column('last_seen', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta', JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    # Use raw SQL to avoid duplicate index error
    op.execute('CREATE INDEX IF NOT EXISTS ix_npc_state_player_id ON npc_state (player_id);')

def downgrade():
    op.execute('DROP INDEX IF EXISTS ix_npc_state_player_id;')
    op.drop_table('npc_state') 