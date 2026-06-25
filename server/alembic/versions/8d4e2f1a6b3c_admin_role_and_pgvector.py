"""admin role and pgvector

Revision ID: 8d4e2f1a6b3c
Revises: 6c110053143f
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d4e2f1a6b3c'
down_revision: Union[str, Sequence[str], None] = '6c110053143f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column('user', sa.Column('role', sa.String(), server_default='user', nullable=False))
    op.add_column('course', sa.Column('is_published', sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('course', 'is_published')
    op.drop_column('user', 'role')
    op.execute("DROP EXTENSION IF EXISTS vector")
