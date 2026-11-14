from django.core.paginator import Paginator
from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from django.conf import settings

from apps.analytics.utils import anonymize_ip, client_ip, country_and_city, parse_ua, referrer_domain

from .models import Book, BookDownload

PER_PAGE = 12


def _visible(request):
    qs = Book.objects.all()
    if not request.user.is_staff:
        qs = qs.filter(published=True)
    return qs


def index(request):
    page = Paginator(Book.objects.filter(published=True), PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'books/index.html', {
        'page': page, 'books': page.object_list,
        'total': page.paginator.count,
    })


def detail(request, slug):
    book = get_object_or_404(_visible(request), slug=slug)
    others = list(Book.objects.filter(published=True).exclude(pk=book.pk)[:3])
    return render(request, 'books/detail.html', {
        'book': book, 'others': others, 'is_preview': not book.published,
    })


def download(request, slug):
    book = get_object_or_404(_visible(request), slug=slug)
    if not book.has_pdf:
        raise Http404('This book has no PDF yet.')
    try:
        handle = book.pdf_file.open('rb')
    except (OSError, ValueError):
        raise Http404('The PDF file is missing.')
    if not request.user.is_staff:
        _log_download(request, book)
    resp = FileResponse(handle, as_attachment=True, filename=book.filename, content_type='application/pdf')
    resp['X-Robots-Tag'] = 'noindex'
    return resp


def _open_pdf(book):
    if not book.has_pdf:
        raise Http404('This book has no PDF yet.')
    try:
        return book.pdf_file.open('rb')
    except (OSError, ValueError):
        raise Http404('The PDF file is missing.')


def read(request, slug):
    """Reader page: the PDF opens inside the site, nothing is downloaded or counted."""
    book = get_object_or_404(_visible(request), slug=slug)
    if not book.has_pdf:
        raise Http404('This book has no PDF yet.')
    return render(request, 'books/read.html', {'book': book, 'is_preview': not book.published})


@xframe_options_sameorigin
def file(request, slug):
    """The PDF shown inline (used by the reader page's frame and 'open in new tab')."""
    book = get_object_or_404(_visible(request), slug=slug)
    resp = FileResponse(_open_pdf(book), as_attachment=False, filename=book.filename, content_type='application/pdf')
    resp['X-Robots-Tag'] = 'noindex'
    return resp


def _log_download(request, book):
    ua = request.META.get('HTTP_USER_AGENT', '')
    device, browser, os_name, is_bot = parse_ua(ua)
    if is_bot:
        return
    ip = client_ip(request)
    country, _city = country_and_city(request, ip)
    if getattr(settings, 'ANALYTICS_ANONYMIZE_IP', False):
        ip = anonymize_ip(ip)
    try:
        ref = referrer_domain(request.META.get('HTTP_REFERER', ''), request.get_host()) or ''
    except Exception:
        ref = ''
    BookDownload.objects.create(book=book, ip=ip, country=(country or '')[:2], device=device[:20],
                                browser=(browser or '')[:40], os=(os_name or '')[:40], referrer=ref[:200])
    Book.objects.filter(pk=book.pk).update(download_count=F('download_count') + 1)
