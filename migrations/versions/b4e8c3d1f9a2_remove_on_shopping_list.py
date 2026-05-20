"""remove on_shopping_list from staple_item

Revision ID: b4e8c3d1f9a2
Revises: a3f9b1c2e4d7
Create Date: 2026-05-20

The on_shopping_list boolean duplicated what is knowable from the existence
of a ShoppingListItem row with that staple_item_id. This migration:

1. (upgrade) Ensures data integrity: creates a ShoppingListItem for any
   staple where on_shopping_list=True but no ShoppingListItem row exists.
2. (upgrade) Drops the on_shopping_list column.
3. (downgrade) Re-adds the column and backfills from ShoppingListItem.

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = 'b4e8c3d1f9a2'
down_revision = 'a3f9b1c2e4d7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Repair any staples where on_shopping_list=True but no ShoppingListItem exists.
    orphaned = conn.execute(sa.text(
        "SELECT s.id, s.name, s.section_id "
        "FROM staple_item s "
        "LEFT JOIN shopping_list_item sli ON sli.staple_item_id = s.id "
        "WHERE s.on_shopping_list AND sli.id IS NULL"
    )).fetchall()

    for staple_id, name, section_id in orphaned:
        conn.execute(sa.text(
            "INSERT INTO shopping_list_item (name, section_id, staple_item_id, checked, created_at) "
            "VALUES (:name, :section_id, :staple_item_id, :checked, :created_at)"
        ), {
            'name': name,
            'section_id': section_id,
            'staple_item_id': staple_id,
            'checked': False,
            'created_at': datetime.now(timezone.utc),
        })

    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.drop_column('on_shopping_list')


def downgrade():
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.add_column(
            sa.Column('on_shopping_list', sa.Boolean(), nullable=False, server_default='0')
        )

    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE staple_item SET on_shopping_list = true "
        "WHERE id IN ("
        "  SELECT DISTINCT staple_item_id FROM shopping_list_item "
        "  WHERE staple_item_id IS NOT NULL"
        ")"
    ))
