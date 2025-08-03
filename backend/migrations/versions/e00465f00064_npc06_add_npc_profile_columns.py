"""npc06_add_npc_profile_columns

Revision ID: e00465f00064
Revises: d707648f34ca
Create Date: 2025-08-03 02:36:25.240691

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e00465f00064'
down_revision: Union[str, Sequence[str], None] = 'd707648f34ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add NPC profile columns for dynamic generation."""
    # Add summary column for NPC backstory
    op.add_column('npc_state', sa.Column('summary', sa.String(), nullable=True))
    
    # Add portrait_url column for NPC images
    op.add_column('npc_state', sa.Column('portrait_url', sa.String(), nullable=True))
    
    # Add baseline_trust column for initial trust values
    op.add_column('npc_state', sa.Column('baseline_trust', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove NPC profile columns."""
    op.drop_column('npc_state', 'baseline_trust')
    op.drop_column('npc_state', 'portrait_url')
    op.drop_column('npc_state', 'summary')
