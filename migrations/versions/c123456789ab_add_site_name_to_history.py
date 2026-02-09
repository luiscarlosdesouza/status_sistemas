"""Add site_name

Revision ID: c123456789ab
Revises: bfea9b20f5f7
"""
from alembic import op
import sqlalchemy as sa

revision = 'c123456789ab'
down_revision = 'bfea9b20f5f7'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('site_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('site_name', sa.String(length=100), nullable=True))
        batch_op.alter_column('site_id', existing_type=sa.INTEGER(), nullable=True)

def downgrade():
    pass
