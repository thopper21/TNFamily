"""add todo model

Revision ID: 997a044bb0f8
Revises: 79a02d0242c4
Create Date: 2026-11-24 10:52:57.806881

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '997a044bb0f8'
down_revision = '79a02d0242c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'todo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('done', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('todo')
