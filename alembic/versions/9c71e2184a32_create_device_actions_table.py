"""create_device_actions_table

Revision ID: 9c71e2184a32
Revises: 8b92d837c412
Create Date: 2026-09-18 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.db.types import GUID, JSONBType

revision: str = '9c71e2184a32'
down_revision: Union[str, Sequence[str], None] = '8b92d837c412'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'device_actions',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_device_id', sa.String(100), nullable=True),
        sa.Column('target_device_id', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('parameters', JSONBType, nullable=False),
        sa.Column('status', sa.String(50), server_default='PENDING', nullable=False),
        sa.Column('result_message', sa.String(500), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_device_actions_id', 'device_actions', ['id'])
    op.create_index('ix_device_actions_user_id', 'device_actions', ['user_id'])
    op.create_index('ix_device_actions_target_device_id', 'device_actions', ['target_device_id'])
    op.create_index('ix_device_actions_status', 'device_actions', ['status'])

def downgrade() -> None:
    op.drop_index('ix_device_actions_status', table_name='device_actions')
    op.drop_index('ix_device_actions_target_device_id', table_name='device_actions')
    op.drop_index('ix_device_actions_user_id', table_name='device_actions')
    op.drop_index('ix_device_actions_id', table_name='device_actions')
    op.drop_table('device_actions')
