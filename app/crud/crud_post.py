from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.schemas.post import PostCreate, PostUpdate

if TYPE_CHECKING:
    from app.models.blog import BlogPost, PostStatusEnum


def get_post(db: Session, post_id: int) -> Optional["BlogPost"]:
    """
    Obtiene un post por su ID.
    """
    from app.models.blog import BlogPost
    return db.query(BlogPost).filter(BlogPost.id == post_id).first()


def get_post_by_slug(db: Session, slug: str) -> Optional["BlogPost"]:
    """
    Obtiene un post por su slug.
    """
    from app.models.blog import BlogPost
    return db.query(BlogPost).filter(BlogPost.slug == slug).first()


def get_posts(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    published_only: bool = False
) -> List["BlogPost"]:
    """
    Obtiene una lista de posts con paginación.
    Si published_only es True, solo devuelve posts publicados.
    """
    from app.models.blog import BlogPost, PostStatusEnum
    query = db.query(BlogPost)
    
    if published_only:
        query = query.filter(BlogPost.status == PostStatusEnum.published)
    
    return query.order_by(desc(BlogPost.created_at)).offset(skip).limit(limit).all()


def create_post(db: Session, post: PostCreate, author_id: int) -> "BlogPost":
    """
    Crea un nuevo post.
    """
    from app.models.blog import BlogPost, PostStatusEnum
    db_post = BlogPost(
        title=post.title,
        slug=post.slug,
        content=post.content,
        author_id=author_id,
        status=post.status,
        category=post.category,
        excerpt=post.excerpt,
        image_url=post.image_url,
        read_time=post.read_time,
        meta_description=post.meta_description,
        faq_json=post.faq_json
    )

    # Si el post se está creando como publicado, establecer published_at
    if post.status == PostStatusEnum.published:
        db_post.published_at = datetime.now(timezone.utc)

    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def update_post(
    db: Session, 
    db_post: "BlogPost", 
    post_update: PostUpdate
) -> "BlogPost":
    """
    Actualiza un post existente.
    """
    from app.models.blog import PostStatusEnum
    update_data = post_update.model_dump(exclude_unset=True)
    
    # Si se está cambiando el estado a publicado y no tenía published_at
    if (
        "status" in update_data 
        and update_data["status"] == PostStatusEnum.published 
        and not db_post.published_at
    ):
        update_data["published_at"] = datetime.now(timezone.utc)
    
    for field, value in update_data.items():
        setattr(db_post, field, value)
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, db_post: "BlogPost") -> "BlogPost":
    """
    Elimina un post.
    """
    db.delete(db_post)
    db.commit()
    return db_post