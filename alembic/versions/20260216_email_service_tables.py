"""Create email service tables

Revision ID: c7e8f9a0b1d2
Revises: ff39ca476f89
Create Date: 2026-02-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7e8f9a0b1d2'
down_revision: Union[str, None] = 'ff39ca476f89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type
    email_status_enum = postgresql.ENUM('queued', 'sent', 'failed', name='email_status_enum', create_type=False)
    email_status_enum.create(op.get_bind(), checkfirst=True)

    # email_projects
    op.create_table(
        'email_projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('api_key_prefix', sa.String(12), nullable=False),
        sa.Column('api_key_expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), server_default='30', nullable=False),
        sa.Column('rate_limit_per_hour', sa.Integer(), server_default='500', nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index('ix_email_projects_api_key_prefix', 'email_projects', ['api_key_prefix'])

    # email_logs
    op.create_table(
        'email_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('email_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_emails', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('cc', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('bcc', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('attachments_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('attachment_names', postgresql.JSONB(), nullable=True),
        sa.Column('status', email_status_enum, nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_email_logs_project_status', 'email_logs', ['project_id', 'status'])
    op.create_index('ix_email_logs_created_at', 'email_logs', ['created_at'])

    # email_escalation_contacts
    op.create_table(
        'email_escalation_contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('email_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # email_escalation_events
    op.create_table(
        'email_escalation_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email_log_id', sa.Integer(), sa.ForeignKey('email_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contact_id', sa.Integer(), sa.ForeignKey('email_escalation_contacts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('notified_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('acknowledged_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('email_escalation_events')
    op.drop_table('email_escalation_contacts')
    op.drop_table('email_logs')
    op.drop_table('email_projects')
    op.execute("DROP TYPE IF EXISTS email_status_enum")
