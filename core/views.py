from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape

from apps.blog.models import Post
from apps.projects.models import Project


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Disallow: /{settings.DASHBOARD_URL}',
        f'Disallow: /{settings.DJANGO_ADMIN_URL}',
        '',
        f'Sitemap: {settings.SITE_URL}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain; charset=utf-8')


STATIC_PAGES = [
    ('home:home', '1.0', 'weekly'),
    ('about:about', '0.8', 'monthly'),
    ('projects:projects', '0.9', 'weekly'),
    ('blog:index', '0.8', 'weekly'),
    ('experience:experience', '0.7', 'monthly'),
    ('skills:skills', '0.6', 'monthly'),
    ('services:services', '0.7', 'monthly'),
    ('contact:contact', '0.6', 'yearly'),
]


def sitemap_xml(request):
    base = settings.SITE_URL
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    latest = Project.objects.filter(published=True).order_by('-updated_at').first()
    for name, prio, freq in STATIC_PAGES:
        lastmod = f'<lastmod>{latest.updated_at:%Y-%m-%d}</lastmod>' if latest and name in ('home:home', 'projects:projects') else ''
        out.append(f'<url><loc>{escape(base + reverse(name))}</loc>{lastmod}<changefreq>{freq}</changefreq><priority>{prio}</priority></url>')
    for p in Project.objects.filter(published=True):
        img = ''
        if p.image:
            img = f'<image:image><image:loc>{escape(base + p.image.url)}</image:loc></image:image>'
        out.append(f'<url><loc>{escape(base + p.get_absolute_url())}</loc><lastmod>{p.updated_at:%Y-%m-%d}</lastmod>'
                   f'<changefreq>monthly</changefreq><priority>0.8</priority>{img}</url>')
    for post in Post.objects.filter(published=True):
        img = f'<image:image><image:loc>{escape(base + post.cover_image.url)}</image:loc></image:image>' if post.cover_image else ''
        out.append(f'<url><loc>{escape(base + post.get_absolute_url())}</loc><lastmod>{post.updated_at:%Y-%m-%d}</lastmod>'
                   f'<changefreq>monthly</changefreq><priority>0.7</priority>{img}</url>')
    out.append('</urlset>')
    return HttpResponse('\n'.join(out), content_type='application/xml; charset=utf-8')


def health(request):
    return HttpResponse('ok', content_type='text/plain')


def page_not_found(request, exception=None):
    return render(request, '404.html', status=404)


def server_error(request):
    # Rendered without context processors so a broken DB can't cause a second failure.
    from django.template import loader
    return HttpResponse(loader.get_template('500.html').render({}), status=500)
