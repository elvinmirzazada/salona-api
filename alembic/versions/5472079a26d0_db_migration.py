"""db migration

Revision ID: 5472079a26d0
Revises: 092058fb5655
Create Date: 2026-03-01 00:19:53.321052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5472079a26d0'
down_revision: Union[str, None] = '092058fb5655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
