"""add product_id to invoice_items

Revision ID: a5b6c7d8e9f0
Revises: e2a4b8c9d012
Create Date: 2026-11-01 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'e2a4b8c9d012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoice_items',
        sa.Column('product_id', sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f('ix_invoice_items_product_id'),
        'invoice_items',
        ['product_id'],
        unique=False
    )
    op.create_foreign_key(
        'fk_invoice_items_product_id_products',
        'invoice_items',
        'products',
        ['product_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_invoice_items_product_id_products', 'invoice_items', type_='foreignkey')
    op.drop_index(op.f('ix_invoice_items_product_id'), table_name='invoice_items')
    op.drop_column('invoice_items', 'product_id')
