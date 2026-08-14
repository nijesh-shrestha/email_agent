"""Add created_at and updated_at to oauth_accounts

Revision ID: add_timestamps_oauth
Revises: 6d4f6f7255f2
Create Date: 2026-08-12 12:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_timestamps_oauth'
down_revision: Union[str, Sequence[str], None] = '6d4f6f7255f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'oauth_accounts',
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.add_column(
        'oauth_accounts',
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_column('oauth_accounts', 'updated_at')
    op.drop_column('oauth_accounts', 'created_at')
