from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime

from app.crud import crud_post
from app.db.session import get_db

router = APIRouter()


@router.get("/robots.txt", response_class=Response)
def get_robots_txt():
    """
    Genera robots.txt para search engines.
    """
    robots_content = """User-agent: *
Allow: /
Allow: /blog
Allow: /blog/*
Disallow: /admin
Disallow: /api/

# Sitemaps
Sitemap: https://www.entersys.mx/api/v1/posts/sitemap.xml
Sitemap: https://api.entersys.mx/api/v1/posts/sitemap.xml

# Crawl delay
Crawl-delay: 1

# Specific bots
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: Slurp
Allow: /

User-agent: DuckDuckBot
Allow: /

User-agent: Baiduspider
Allow: /

User-agent: YandexBot
Allow: /

User-agent: facebookexternalhit
Allow: /

User-agent: Twitterbot
Allow: /

User-agent: LinkedInBot
Allow: /

User-agent: WhatsApp
Allow: /

# AI Crawlers
User-agent: GPTBot
Allow: /blog
Allow: /blog/*

User-agent: ChatGPT-User
Allow: /blog
Allow: /blog/*

User-agent: CCBot
Allow: /blog
Allow: /blog/*

User-agent: anthropic-ai
Allow: /blog
Allow: /blog/*

User-agent: Claude-Web
Allow: /blog
Allow: /blog/*

User-agent: Google-Extended
Allow: /blog
Allow: /blog/*
"""

    return Response(
        content=robots_content,
        media_type="text/plain",
        headers={"Content-Type": "text/plain; charset=utf-8"}
    )


@router.get("/rss.xml", response_class=Response)
def get_rss_feed(db: Session = Depends(get_db)):
    """
    Genera RSS feed para el blog.
    """
    posts = crud_post.get_posts(db=db, skip=0, limit=50, published_only=True)

    base_url = "https://www.entersys.mx"

    rss_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    rss_xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
    rss_xml += '  <channel>\n'
    rss_xml += '    <title>Entersys Blog</title>\n'
    rss_xml += f'    <link>{base_url}/blog</link>\n'
    rss_xml += '    <description>Transformamos operaciones empresariales con Worksys y Expersys. Artículos sobre automatización, gestión de calidad y mejora continua.</description>\n'
    rss_xml += '    <language>es-MX</language>\n'
    rss_xml += f'    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>\n'
    rss_xml += f'    <atom:link href="{base_url}/api/v1/seo/rss.xml" rel="self" type="application/rss+xml"/>\n'
    rss_xml += '    <generator>Entersys Blog Engine</generator>\n'
    rss_xml += '    <image>\n'
    rss_xml += f'      <url>{base_url}/logo.png</url>\n'
    rss_xml += '      <title>Entersys</title>\n'
    rss_xml += f'      <link>{base_url}</link>\n'
    rss_xml += '    </image>\n'

    for post in posts:
        rss_xml += '    <item>\n'
        rss_xml += f'      <title><![CDATA[{post.title}]]></title>\n'
        rss_xml += f'      <link>{base_url}/blog/{post.slug}</link>\n'
        rss_xml += f'      <guid isPermaLink="true">{base_url}/blog/{post.slug}</guid>\n'

        if post.excerpt:
            rss_xml += f'      <description><![CDATA[{post.excerpt}]]></description>\n'

        if post.content:
            # Truncate content for RSS
            content_preview = post.content[:500] + '...' if len(post.content) > 500 else post.content
            rss_xml += f'      <content:encoded><![CDATA[{content_preview}]]></content:encoded>\n'

        if post.category:
            rss_xml += f'      <category><![CDATA[{post.category}]]></category>\n'

        rss_xml += '      <dc:creator><![CDATA[Entersys]]></dc:creator>\n'

        pub_date = post.published_at or post.created_at
        if pub_date:
            if isinstance(pub_date, str):
                try:
                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    pub_date = datetime.now()
            rss_xml += f'      <pubDate>{pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>\n'

        if post.image_url:
            rss_xml += '      <enclosure url="{}" type="image/jpeg"/>\n'.format(post.image_url)

        rss_xml += '    </item>\n'

    rss_xml += '  </channel>\n'
    rss_xml += '</rss>'

    return Response(
        content=rss_xml,
        media_type="application/xml",
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Cache-Control": "public, max-age=3600"
        }
    )
