"""initial

Revision ID: a3f9b1c2e4d7
Revises:
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f9b1c2e4d7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_id', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=256), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('profile_picture_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_table(
        'store_section',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'staple_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('on_shopping_list', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['section_id'], ['store_section.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'shopping_list_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('staple_item_id', sa.Integer(), nullable=True),
        sa.Column('checked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['section_id'], ['store_section.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['staple_item_id'], ['staple_item.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('shopping_list_item')
    op.drop_table('staple_item')
    op.drop_table('store_section')
    op.drop_table('user')
