"""add pricing_config to upstreams

Revision ID: a1b2c3d4e5f6
Revises: f321205629d4
Create Date: 2026-06-20 09:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f321205629d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('upstreams', sa.Column('pricing_config', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('upstreams', 'pricing_config')
