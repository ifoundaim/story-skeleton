"""
NPC03: Extend NPC table with metadata fields for dynamic generation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = 'npc03_extend_npc_metadata'
down_revision = 'npc02_create_npc_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add new metadata columns to the npc table
    op.add_column('npc', sa.Column('role', sa.String, nullable=True))
    op.add_column('npc', sa.Column('archetype', sa.String, nullable=True))
    op.add_column('npc', sa.Column('personality_traits', JSON, nullable=True, default=list))
    op.add_column('npc', sa.Column('narrative_hooks', JSON, nullable=True, default=list))
    op.add_column('npc', sa.Column('relationship_to_player', sa.String, nullable=True))
    op.add_column('npc', sa.Column('motivation', sa.String, nullable=True))
    op.add_column('npc', sa.Column('secrets', JSON, nullable=True, default=list))
    op.add_column('npc', sa.Column('generated', sa.String, nullable=True))

def downgrade():
    # Remove the added columns
    op.drop_column('npc', 'generated')
    op.drop_column('npc', 'secrets')
    op.drop_column('npc', 'motivation')
    op.drop_column('npc', 'relationship_to_player')
    op.drop_column('npc', 'narrative_hooks')
    op.drop_column('npc', 'personality_traits')
    op.drop_column('npc', 'archetype')
    op.drop_column('npc', 'role') 