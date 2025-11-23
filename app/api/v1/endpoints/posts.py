from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
from html import escape

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


@router.get("/sitemap.xml", response_class=Response)
def generate_sitemap(db: Session = Depends(get_db)):
    """
    Genera el sitemap.xml para los posts del blog.
    Este endpoint está disponible públicamente para search engines.
    """
    posts = crud_post.get_posts(db=db, skip=0, limit=1000, published_only=True)
    base_url = "https://www.entersys.mx"

    # Construir el sitemap XML manualmente con escape correcto
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    sitemap_xml += 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'

    # Agregar página principal del blog
    sitemap_xml += '  <url>\n'
    sitemap_xml += f'    <loc>{base_url}/blog</loc>\n'
    sitemap_xml += f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
    sitemap_xml += '    <changefreq>daily</changefreq>\n'
    sitemap_xml += '    <priority>1.0</priority>\n'
    sitemap_xml += '  </url>\n'

    # Agregar cada post
    for post in posts:
        sitemap_xml += '  <url>\n'
        sitemap_xml += f'    <loc>{escape(f"{base_url}/blog/{post.slug}")}</loc>\n'

        # Usar updated_at si existe, sino published_at, sino created_at
        last_mod = post.updated_at or post.published_at or post.created_at
        if last_mod:
            if isinstance(last_mod, str):
                last_mod_str = last_mod.split('T')[0]
            else:
                last_mod_str = last_mod.strftime("%Y-%m-%d")
            sitemap_xml += f'    <lastmod>{last_mod_str}</lastmod>\n'

        sitemap_xml += '    <changefreq>weekly</changefreq>\n'
        sitemap_xml += '    <priority>0.8</priority>\n'

        # Agregar imagen si existe
        if post.image_url:
            sitemap_xml += '    <image:image>\n'
            sitemap_xml += f'      <image:loc>{escape(post.image_url)}</image:loc>\n'
            if post.title:
                sitemap_xml += f'      <image:title>{escape(post.title)}</image:title>\n'
            sitemap_xml += '    </image:image>\n'

        sitemap_xml += '  </url>\n'

    sitemap_xml += '</urlset>'

    return Response(
        content=sitemap_xml.encode('utf-8'),
        media_type="application/xml",
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/by-id/{post_id}", response_model=Post)
def read_post_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: "AdminUser" = Depends(get_current_user),
):
    """
    Obtiene un post específico por su ID (protegido - requiere autenticación).
    Usado por el panel de administración para editar posts.
    """
    post = crud_post.get_post(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


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