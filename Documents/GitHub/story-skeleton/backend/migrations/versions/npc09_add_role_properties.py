"""npc09 add role properties

Revision ID: npc09_add_role_properties
Revises: sm01_init_soulmap
Create Date: 2025-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'npc09_add_role_properties'
# Attach to the NPC branch since we alter the 'npc' table
down_revision = 'npc02_create_npc_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to npc table if present
    try:
        op.add_column('npc', sa.Column('role_label', sa.Text(), nullable=True))
        op.add_column('npc', sa.Column('role_aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
        op.add_column('npc', sa.Column('function_probs', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column('npc', sa.Column('stance_probs', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column('npc', sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column('npc', sa.Column('role_confidence', sa.Float(), nullable=True))
        # role_embedding optional – if pgvector available
        try:
            op.add_column('npc', sa.Column('role_embedding', sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True))
        except Exception:
            pass
        op.add_column('npc', sa.Column('last_role_update_scene', sa.Integer(), nullable=True))
    except Exception:
        pass


def downgrade():
    try:
        op.drop_column('npc', 'last_role_update_scene')
        op.drop_column('npc', 'role_embedding')
        op.drop_column('npc', 'role_confidence')
        op.drop_column('npc', 'capabilities')
        op.drop_column('npc', 'stance_probs')
        op.drop_column('npc', 'function_probs')
        op.drop_column('npc', 'role_aliases')
        op.drop_column('npc', 'role_label')
    except Exception:
        pass


