"""create invoices and invoice_items tables

Revision ID: e2a4b8c9d012
Revises: fdc5992b8333
Create Date: 2026-11-01 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a4b8c9d012'
down_revision: Union[str, Sequence[str], None] = 'fdc5992b8333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('supplier', sa.String(length=255), nullable=False),
        sa.Column('invoice_number', sa.String(length=100), nullable=False, server_default='—'),
        sa.Column('date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('total', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_supplier'), 'invoices', ['supplier'], unique=False)

    # Create invoice_items table
    op.create_table(
        'invoice_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_items_id'), 'invoice_items', ['id'], unique=False)
    op.create_index(op.f('ix_invoice_items_invoice_id'), 'invoice_items', ['invoice_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoice_items_invoice_id'), table_name='invoice_items')
    op.drop_index(op.f('ix_invoice_items_id'), table_name='invoice_items')
    op.drop_table('invoice_items')
    op.drop_index(op.f('ix_invoices_supplier'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')
