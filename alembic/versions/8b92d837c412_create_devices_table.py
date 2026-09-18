"""create_devices_table

Revision ID: 8b92d837c412
Revises: 01f7e011a288
Create Date: 2026-09-16 13:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.db.types import GUID, JSONBType

revision: str = '8b92d837c412'
down_revision: Union[str, Sequence[str], None] = '01f7e011a288'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'devices',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(100), nullable=False),
        sa.Column('device_type', sa.String(50), server_default='desktop', nullable=False),
        sa.Column('device_name', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), server_default='windows', nullable=False),
        sa.Column('app_version', sa.String(50), nullable=True),
        sa.Column('capabilities', JSONBType, nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_devices_id', 'devices', ['id'])
    op.create_index('ix_devices_user_id', 'devices', ['user_id'])
    op.create_index('ix_devices_device_id', 'devices', ['device_id'])

def downgrade() -> None:
    op.drop_index('ix_devices_device_id', table_name='devices')
    op.drop_index('ix_devices_user_id', table_name='devices')
    op.drop_index('ix_devices_id', table_name='devices')
    op.drop_table('devices')
