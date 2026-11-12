from django.conf import settings
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape
from django.utils.http import http_date
from django.core.paginator import Paginator

from .models import Category, Post


def _published():
    return Post.objects.filter(published=True).select_related('category')



def index(request):
    qs = _published()
    categories = Category.objects.all()
    active = categories.filter(slug=request.GET.get('c', '')).first()
    if active:
        qs = qs.filter(category=active)
    posts = list(qs)
    featured = next((p for p in posts if p.featured), posts[0] if posts else None)
    ordered = ([featured] + [p for p in posts if p is not featured]) if featured else []
    page = Paginator(ordered, 9).get_page(request.GET.get('page'))
    return render(request, 'blog/index.html',
        {
          'page': page,
          'posts_all': page.object_list,
          'featured': featured,
          'categories': categories,
          'active_category': active,
    })

def detail(request, slug):
    qs = Post.objects.select_related('category')
    if not request.user.is_staff:
        qs = qs.filter(published=True)
    post = get_object_or_404(qs, slug=slug)
    pub = _published().exclude(pk=post.pk)
    cond = Q()
    if post.category_id: # type: ignore
        cond |= Q(category_id=post.category_id) # type: ignore
    for t in post.tag_list:
        cond |= Q(tags__icontains=t)
    related = list(pub.filter(cond)[:3]) if cond else []
    if len(related) < 3:
        extra = pub.exclude(pk__in=[r.pk for r in related])[:3 - len(related)]
        related += list(extra)
    prev_post = pub.filter(published_at__lt=post.published_at).order_by('-published_at').first()
    next_post = pub.filter(published_at__gt=post.published_at).order_by('published_at').first()
    return render(request, 'blog/detail.html', {
        'post': post, 'related': related, 'prev_post': prev_post, 'next_post': next_post,
        'is_preview': not post.published,
    })


def feed(request):
    base = settings.SITE_URL
    posts = list(_published()[:30])
    items = []
    for p in posts:
        link = escape(base + p.get_absolute_url())
        items.append(
            f'<item><title>{escape(p.title)}</title><link>{link}</link><guid isPermaLink="true">{link}</guid>'
            f'<pubDate>{http_date(p.published_at.timestamp())}</pubDate>'
            + (f'<category>{escape(p.category.name)}</category>' if p.category else '')
            + f'<description>{escape(p.excerpt)}</description></item>')
    last = http_date(posts[0].published_at.timestamp()) if posts else http_date(0)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
           f'<title>Blog | Muhammad Nouman</title><link>{escape(base)}/blog/</link>'
           '<description>Notes on Django, system design and shipping backends.</description><language>en</language>'
           f'<lastBuildDate>{last}</lastBuildDate>' + ''.join(items) + '</channel></rss>')
    return HttpResponse(xml, content_type='application/rss+xml; charset=utf-8')
