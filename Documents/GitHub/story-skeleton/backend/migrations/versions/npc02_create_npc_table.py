"""
NPC02: Create npc table with full_name, baseline_trust, trust
"""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID

revision = 'npc02_create_npc_table'
down_revision = 'npc01_init_npc_state'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'npc',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('full_name', sa.String, nullable=False),
        sa.Column('baseline_trust', sa.Float, nullable=False, default=0.0),
        sa.Column('trust', sa.Float, nullable=False, default=0.0),
    )
    # Create index on id for faster lookups
    op.create_index('ix_npc_id', 'npc', ['id'])

def downgrade():
    op.drop_index('ix_npc_id', 'npc')
    op.drop_table('npc') 