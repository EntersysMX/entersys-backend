"""add_blog_post_fields

Revision ID: ff39ca476f89
Revises: 8b25b5aeef53
Create Date: 2025-10-22 02:59:10.021237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff39ca476f89'
down_revision: Union[str, Sequence[str], None] = '8b25b5aeef53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to blog_posts table
    op.add_column('blog_posts', sa.Column('category', sa.String(50), server_default='Tecnología', nullable=True))
    op.add_column('blog_posts', sa.Column('excerpt', sa.Text(), nullable=True))
    op.add_column('blog_posts', sa.Column('image_url', sa.String(500), nullable=True))
    op.add_column('blog_posts', sa.Column('read_time', sa.String(20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from blog_posts table
    op.drop_column('blog_posts', 'read_time')
    op.drop_column('blog_posts', 'image_url')
    op.drop_column('blog_posts', 'excerpt')
    op.drop_column('blog_posts', 'category')
