"""add subcategories support

Revision ID: add_subcategories_support
Revises: 7bf17463b345
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_subcategories_support'
down_revision = '7bf17463b345'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_category_id column to company_categories table
    op.add_column('company_categories',
                  sa.Column('parent_category_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_company_categories_parent',
        'company_categories', 'company_categories',
        ['parent_category_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add index for better query performance
    op.create_index('ix_company_categories_parent_category_id',
                    'company_categories', ['parent_category_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_company_categories_parent_category_id', table_name='company_categories')

    # Drop foreign key constraint
    op.drop_constraint('fk_company_categories_parent', 'company_categories', type_='foreignkey')

    # Drop column
    op.drop_column('company_categories', 'parent_category_id')

