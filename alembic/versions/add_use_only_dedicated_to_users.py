"""add_use_only_dedicated_to_users

Revision ID: a1b2c3d4e5f6
Revises: 0dcd8c4a8684
Create Date: 2025-12-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0dcd8c4a8684'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add use_only_dedicated field to users table with default value False
    op.add_column('users', sa.Column('use_only_dedicated', sa.Boolean(), nullable=False, server_default='0', comment='是否仅使用用户自己创建的专属账号'))


def downgrade() -> None:
    # Remove use_only_dedicated field from users table
    op.drop_column('users', 'use_only_dedicated')
