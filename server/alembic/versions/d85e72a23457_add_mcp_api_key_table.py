"""add mcp_api_key table

Revision ID: d85e72a23457
Revises: a1b2c3d4e5f6
Create Date: 2026-06-30 09:33:29.819573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd85e72a23457'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'mcp_api_key',
        sa.Column('id', sa.String(length=30), nullable=False),
        sa.Column('user_id', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=24), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index(op.f('ix_mcp_api_key_user_id'), 'mcp_api_key', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_mcp_api_key_user_id'), table_name='mcp_api_key')
    op.drop_table('mcp_api_key')
