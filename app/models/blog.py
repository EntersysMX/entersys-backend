# app/models/blog.py
import enum
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, ForeignKey,
    TIMESTAMP, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base

class PostStatusEnum(enum.Enum):
    draft = "draft"
    published = "published"

class AdminUser(Base):
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, server_default='true', nullable=False)
    posts = relationship("BlogPost", back_populates="author", cascade="all, delete-orphan")

class BlogPost(Base):
    __tablename__ = 'blog_posts'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    content = Column(Text)
    author_id = Column(Integer, ForeignKey('admin_users.id', ondelete='RESTRICT'), nullable=False)
    status = Column(
        SAEnum(PostStatusEnum, name='post_status_enum', create_type=False),
        nullable=False, server_default=PostStatusEnum.draft.value
    )
    published_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
    meta_description = Column(String(300))
    faq_json = Column(JSONB)
    author = relationship("AdminUser", back_populates="posts")