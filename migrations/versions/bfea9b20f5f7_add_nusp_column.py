"""Add nusp column

Revision ID: bfea9b20f5f7
Revises: 77c27cedd60d
Create Date: 2026-02-05 16:35:18.517774

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bfea9b20f5f7'
down_revision = '77c27cedd60d'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite-safe replacement for adding nullable column
    try:
        op.add_column('user', sa.Column('nusp', sa.String(length=20), nullable=True))
    except Exception:
        pass # Ignore if column already exists

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('nusp')
