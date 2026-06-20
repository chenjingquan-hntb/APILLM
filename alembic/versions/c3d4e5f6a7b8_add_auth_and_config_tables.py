"""add user roles, sessions, logs, model configs, upstream bindings

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Modify users table ===
    op.add_column('users', sa.Column('password_hash', sa.String(length=256), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=16), nullable=False, server_default='user'))

    # === Create user_sessions table ===
    op.create_table('user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=128), nullable=False),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token_hash'),
    )

    # === Create usage_logs table ===
    op.create_table('usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(length=128), nullable=False),
        sa.Column('upstream_id', sa.Integer(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Numeric(precision=12, scale=8), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id']),
        sa.ForeignKeyConstraint(['upstream_id'], ['upstreams.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # === Create model_configs table ===
    op.create_table('model_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=128), nullable=False),
        sa.Column('display_name', sa.String(length=128), nullable=True),
        sa.Column('group_name', sa.String(length=64), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=16), nullable=True),
        sa.Column('manual_prompt_price', sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column('manual_completion_price', sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id'),
    )

    # === Create upstream_models table ===
    op.create_table('upstream_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upstream_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.String(length=128), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['upstream_id'], ['upstreams.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # === Indexes for performance ===
    op.create_index('ix_usage_logs_user_id', 'usage_logs', ['user_id'])
    op.create_index('ix_usage_logs_created_at', 'usage_logs', ['created_at'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_user_sessions_user_id')
    op.drop_index('ix_usage_logs_created_at')
    op.drop_index('ix_usage_logs_user_id')

    op.drop_table('upstream_models')
    op.drop_table('model_configs')
    op.drop_table('usage_logs')
    op.drop_table('user_sessions')

    op.drop_column('users', 'role')
    op.drop_column('users', 'password_hash')
