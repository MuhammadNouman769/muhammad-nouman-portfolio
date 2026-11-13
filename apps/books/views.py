from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from .models import Book


def _published():
    return Book.objects.filter(published=True)


def index(request):
    qs = _published()
    cats = sorted({c for c in qs.values_list('category', flat=True) if c})
    active = request.GET.get('c', '').strip()
    q = request.GET.get('q', '').strip()
    if active in cats:
        qs = qs.filter(category=active)
    else:
        active = ''
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(subtitle__icontains=q))
    books = sorted(qs, key=lambda b: (not b.featured,))  # stable: featured first, keeps dashboard order
    page = Paginator(books, 12).get_page(request.GET.get('page'))
    return render(request, 'books/index.html', {
        'page': page, 'books': page.object_list, 'categories': cats, 'active_category': active, 'q': q,
        'total': len(books),
    })


def detail(request, slug):
    qs = Book.objects.all() if request.user.is_staff else _published()
    book = get_object_or_404(qs, slug=slug)
    others = list(_published().exclude(pk=book.pk)[:4])
    return render(request, 'books/detail.html', {'book': book, 'others': others, 'is_preview': not book.published})


def download(request, slug):
    book = get_object_or_404(_published(), slug=slug)
    if not book.pdf_file:
        raise Http404('No PDF for this book yet.')
    try:
        fh = book.pdf_file.open('rb')
    except (FileNotFoundError, ValueError, OSError):
        raise Http404('The PDF file is missing.')
    Book.objects.filter(pk=book.pk).update(downloads=F('downloads') + 1)
    return FileResponse(fh, as_attachment=True, filename=f'{book.slug}.pdf', content_type='application/pdf')
