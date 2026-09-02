"""add_planner_notifications_study_and_calendar

Revision ID: 01f7e011a288
Revises: 7a5478824875
Create Date: 2026-09-02 11:01:09.138864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.db.types import GUID, JSONBType

# revision identifiers, used by Alembic.
revision: str = '01f7e011a288'
down_revision: Union[str, Sequence[str], None] = '7a5478824875'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. planner_tasks
    op.create_table(
        'planner_tasks',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), server_default='General', nullable=False),
        sa.Column('priority', sa.String(20), server_default='medium', nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subtasks', JSONBType, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_planner_tasks_id'), 'planner_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_planner_tasks_user_id'), 'planner_tasks', ['user_id'], unique=False)

    # 2. notifications
    op.create_table(
        'notifications',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), server_default='briefing', nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('action_payload', JSONBType, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    # 3. subjects
    op.create_table(
        'subjects',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(20), server_default='#2563EB', nullable=False),
        sa.Column('priority', sa.String(20), server_default='medium', nullable=False),
        sa.Column('exam_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_subjects_id'), 'subjects', ['id'], unique=False)
    op.create_index(op.f('ix_subjects_user_id'), 'subjects', ['user_id'], unique=False)

    # 4. assignments
    op.create_table(
        'assignments',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('subject_id', GUID(), sa.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('subject_name', sa.String(100), server_default='General', nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_time', sa.String(20), nullable=True),
        sa.Column('priority', sa.String(20), server_default='medium', nullable=False),
        sa.Column('status', sa.String(20), server_default='NOT_STARTED', nullable=False),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_assignments_id'), 'assignments', ['id'], unique=False)
    op.create_index(op.f('ix_assignments_user_id'), 'assignments', ['user_id'], unique=False)

    # 5. calendar_events
    op.create_table(
        'calendar_events',
        sa.Column('id', GUID(), primary_key=True, nullable=False),
        sa.Column('user_id', GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(50), server_default='study_session', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_all_day', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('color', sa.String(20), server_default='#2563EB', nullable=False),
        sa.Column('status', sa.String(20), server_default='scheduled', nullable=False),
        sa.Column('related_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_calendar_events_id'), 'calendar_events', ['id'], unique=False)
    op.create_index(op.f('ix_calendar_events_user_id'), 'calendar_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_calendar_events_user_id'), table_name='calendar_events')
    op.drop_index(op.f('ix_calendar_events_id'), table_name='calendar_events')
    op.drop_table('calendar_events')

    op.drop_index(op.f('ix_assignments_user_id'), table_name='assignments')
    op.drop_index(op.f('ix_assignments_id'), table_name='assignments')
    op.drop_table('assignments')

    op.drop_index(op.f('ix_subjects_user_id'), table_name='subjects')
    op.drop_index(op.f('ix_subjects_id'), table_name='subjects')
    op.drop_table('subjects')

    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')

    op.drop_index(op.f('ix_planner_tasks_user_id'), table_name='planner_tasks')
    op.drop_index(op.f('ix_planner_tasks_id'), table_name='planner_tasks')
    op.drop_table('planner_tasks')
