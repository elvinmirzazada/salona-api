"""initial migration

Revision ID: 04d9ebd854b3
Revises: 
Create Date: 2025-07-27 18:54:42.817868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('business_staff',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=True),
        sa.Column('professional_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['professional_id'], ['professionals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_business_staff_id'), 'business_staff', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_business_staff_id'), table_name='business_staff')
    op.drop_table('business_staff')
