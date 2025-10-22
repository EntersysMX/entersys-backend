from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
import xml.etree.ElementTree as ET

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

    # Base URL del sitio
    base_url = "https://www.entersys.mx"

    # Crear elemento raíz con namespaces
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    ET.register_namespace('image', 'http://www.google.com/schemas/sitemap-image/1.1')

    urlset = ET.Element('urlset', {
        'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'xmlns:image': 'http://www.google.com/schemas/sitemap-image/1.1'
    })

    # Agregar página principal del blog
    url_blog = ET.SubElement(urlset, 'url')
    ET.SubElement(url_blog, 'loc').text = f'{base_url}/blog'
    ET.SubElement(url_blog, 'lastmod').text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(url_blog, 'changefreq').text = 'daily'
    ET.SubElement(url_blog, 'priority').text = '1.0'

    # Agregar cada post
    for post in posts:
        url_elem = ET.SubElement(urlset, 'url')
        ET.SubElement(url_elem, 'loc').text = f'{base_url}/blog/{post.slug}'

        # Usar updated_at si existe, sino published_at, sino created_at
        last_mod = post.updated_at or post.published_at or post.created_at
        if last_mod:
            if isinstance(last_mod, str):
                last_mod_str = last_mod.split('T')[0]
            else:
                last_mod_str = last_mod.strftime("%Y-%m-%d")
            ET.SubElement(url_elem, 'lastmod').text = last_mod_str

        ET.SubElement(url_elem, 'changefreq').text = 'weekly'
        ET.SubElement(url_elem, 'priority').text = '0.8'

        # Agregar imagen si existe
        if post.image_url:
            image_elem = ET.SubElement(url_elem, '{http://www.google.com/schemas/sitemap-image/1.1}image')
            ET.SubElement(image_elem, '{http://www.google.com/schemas/sitemap-image/1.1}loc').text = post.image_url
            if post.title:
                ET.SubElement(image_elem, '{http://www.google.com/schemas/sitemap-image/1.1}title').text = post.title

    # Convertir a string XML
    xml_str = ET.tostring(urlset, encoding='utf-8', method='xml')
    sitemap_xml = b'<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    return Response(
        content=sitemap_xml,
        media_type="application/xml",
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600"
        }
    )


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