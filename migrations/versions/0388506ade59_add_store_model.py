"""add store model

Revision ID: 0388506ade59
Revises: b4e8c3d1f9a2
Create Date: 2026-08-31 16:31:50.574237

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0388506ade59'
down_revision = 'b4e8c3d1f9a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO store (name) VALUES ('Grocery')"))
    default_id = conn.execute(sa.text("SELECT id FROM store WHERE name = 'Grocery'")).scalar()

    # store_section: add store_id (nullable), backfill, then alter NOT NULL + fix unique constraint
    with op.batch_alter_table('store_section') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE store_section SET store_id = :sid"), {'sid': default_id})
    if conn.dialect.name == 'postgresql':
        # recreate='always' would DROP store_section, which PostgreSQL rejects while
        # staple_item and shopping_list_item hold FK references to it.
        with op.batch_alter_table('store_section') as batch_op:
            batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
            batch_op.drop_constraint('store_section_name_key', type_='unique')
            batch_op.create_foreign_key('fk_store_section_store_id', 'store', ['store_id'], ['id'], ondelete='CASCADE')
            batch_op.create_unique_constraint('uq_store_section_store_name', ['store_id', 'name'])
    else:
        with op.batch_alter_table('store_section', recreate='always') as batch_op:
            batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
            batch_op.create_foreign_key('fk_store_section_store_id', 'store', ['store_id'], ['id'], ondelete='CASCADE')
            batch_op.create_unique_constraint('uq_store_section_store_name', ['store_id', 'name'])

    # staple_item: add store_id (nullable), backfill, alter NOT NULL + FK
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE staple_item SET store_id = :sid"), {'sid': default_id})
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_staple_item_store_id', 'store', ['store_id'], ['id'], ondelete='CASCADE')

    # shopping_list_item: add store_id (nullable), backfill, alter NOT NULL + FK
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE shopping_list_item SET store_id = :sid"), {'sid': default_id})
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_shopping_list_item_store_id', 'store', ['store_id'], ['id'], ondelete='CASCADE')


def downgrade():
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.drop_constraint('fk_shopping_list_item_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.drop_constraint('fk_staple_item_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        with op.batch_alter_table('store_section') as batch_op:
            batch_op.drop_constraint('uq_store_section_store_name', type_='unique')
            batch_op.drop_constraint('fk_store_section_store_id', type_='foreignkey')
            batch_op.drop_column('store_id')
            batch_op.create_unique_constraint('store_section_name_key', ['name'])
    else:
        with op.batch_alter_table('store_section', recreate='always') as batch_op:
            batch_op.drop_constraint('uq_store_section_store_name', type_='unique')
            batch_op.drop_constraint('fk_store_section_store_id', type_='foreignkey')
            batch_op.drop_column('store_id')
            batch_op.create_unique_constraint('uq_store_section_name', ['name'])
    op.drop_table('store')
