from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.blog import PostStatusEnum


class PostBase(BaseModel):
    """
    Schema base para las propiedades compartidas de un post.
    """
    title: str
    slug: str
    content: Optional[str] = None
    status: PostStatusEnum = PostStatusEnum.draft
    meta_description: Optional[str] = None
    faq_json: Optional[dict] = None


class PostCreate(PostBase):
    """
    Schema para crear un nuevo post.
    """
    pass


class PostUpdate(BaseModel):
    """
    Schema para actualizar un post.
    """
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    status: Optional[PostStatusEnum] = None
    meta_description: Optional[str] = None
    faq_json: Optional[dict] = None


class PostInDBBase(PostBase):
    """
    Schema con propiedades adicionales que se obtienen de la base de datos.
    """
    id: int
    author_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Post(PostInDBBase):
    """
    Schema para devolver un post (con información del autor).
    """
    pass


class PostInDB(PostInDBBase):
    """
    Schema para propiedades adicionales almacenadas en la base de datos.
    """
    pass