"""merge npc03 and sm02 heads

Revision ID: 8b8bf78d568f
Revises: npc03_extend_npc_metadata, sm02_update_soulmap_table
Create Date: 2025-08-05 01:40:40.975328

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b8bf78d568f'
down_revision: Union[str, Sequence[str], None] = ('npc03_extend_npc_metadata', 'sm02_update_soulmap_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
