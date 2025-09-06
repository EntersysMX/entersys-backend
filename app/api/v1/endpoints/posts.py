from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import crud_post
from app.db.session import get_db
from app.schemas.post import Post, PostCreate, PostUpdate

router = APIRouter()


@router.get("/", response_model=List[Post])
def read_posts(
    skip: int = 0,
    limit: int = 100,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Obtiene una lista de posts.
    Por defecto solo muestra los posts publicados (público).
    """
    posts = crud_post.get_posts(
        db=db, skip=skip, limit=limit, published_only=published_only
    )
    return posts


@router.get("/{slug}", response_model=Post)
def read_post_by_slug(
    slug: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene un post específico por su slug (público).
    """
    post = crud_post.get_post_by_slug(db=db, slug=slug)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found"
        )
    return post


@router.post("/", response_model=Post, status_code=status.HTTP_201_CREATED)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: "AdminUser" = Depends(get_current_user),
):
    """
    Crea un nuevo post (protegido - requiere autenticación).
    """
    # Verificar que el slug no exista
    if crud_post.get_post_by_slug(db=db, slug=post.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A post with this slug already exists"
        )
    
    return crud_post.create_post(db=db, post=post, author_id=current_user.id)


@router.put("/{post_id}", response_model=Post)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: "AdminUser" = Depends(get_current_user),
):
    """
    Actualiza un post existente (protegido - requiere autenticación).
    """
    post = crud_post.get_post(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found"
        )
    
    # Si se está actualizando el slug, verificar que no exista
    if post_update.slug and post_update.slug != post.slug:
        if crud_post.get_post_by_slug(db=db, slug=post_update.slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A post with this slug already exists"
            )
    
    return crud_post.update_post(db=db, db_post=post, post_update=post_update)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: "AdminUser" = Depends(get_current_user),
):
    """
    Elimina un post (protegido - requiere autenticación).
    """
    post = crud_post.get_post(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found"
        )
    
    crud_post.delete_post(db=db, db_post=post)
    return {"message": "Post deleted successfully"}