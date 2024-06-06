"""add streak saver field to screams

Revision ID: af162e382559
Revises: 9136490b3f27
Create Date: 2024-06-06 06:29:10.796818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af162e382559'
down_revision: Union[str, None] = '9136490b3f27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dc_screams', sa.Column('sc_streak_last', sa.INTEGER(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column('dc_screams', 'sc_streak_last')
