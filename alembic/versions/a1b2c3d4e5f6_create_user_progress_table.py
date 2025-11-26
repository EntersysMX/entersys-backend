"""create_user_progress_table

Revision ID: a1b2c3d4e5f6
Revises: ff39ca476f89
Create Date: 2025-11-26 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ff39ca476f89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_progress table for video security module (MD050)."""
    op.create_table(
        'user_progress',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(50), nullable=False),
        sa.Column('seconds_accumulated', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'video_id', name='uq_user_video')
    )
    op.create_index('ix_user_progress_user_id', 'user_progress', ['user_id'])
    op.create_index('ix_user_progress_video_id', 'user_progress', ['video_id'])


def downgrade() -> None:
    """Drop user_progress table."""
    op.drop_index('ix_user_progress_video_id', table_name='user_progress')
    op.drop_index('ix_user_progress_user_id', table_name='user_progress')
    op.drop_table('user_progress')
