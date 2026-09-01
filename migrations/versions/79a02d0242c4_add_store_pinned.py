"""add store pinned

Revision ID: 79a02d0242c4
Revises: 0388506ade59
Create Date: 2026-08-31 17:10:19.598467

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '79a02d0242c4'
down_revision = '0388506ade59'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('store') as batch_op:
        batch_op.add_column(sa.Column('pinned', sa.Boolean(), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE store SET pinned = FALSE"))

    with op.batch_alter_table('store') as batch_op:
        batch_op.alter_column('pinned', existing_type=sa.Boolean(), nullable=False)


def downgrade():
    with op.batch_alter_table('store') as batch_op:
        batch_op.drop_column('pinned')
