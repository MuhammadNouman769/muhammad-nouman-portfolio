from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Project


def _published():
    return Project.objects.filter(published=True).prefetch_related('tags')


def case_studies():
    return Project.objects.filter(published=True, case_study=True).prefetch_related('tags', 'features').order_by('order_in_showcase', 'order', '-id')


def case_studies_page(request):
    items = list(case_studies())
    context = _project_listing_context(request)
    context['case_studies'] = items
    return render(request, 'projects/casestudy.html', context)


def _project_listing_context(request):
    queryset = _published().order_by('order', '-id')
    published = Project.objects.filter(published=True)
    statuses = [(key, label) for key, label in Project.STATUS_CHOICES
                if published.filter(status=key).exists()]
    tags = list(published.values_list('tags__name', flat=True).distinct().order_by('tags__name'))
    tags = [tag for tag in tags if tag]
    status_filters = []
    for key, label in [('', 'All'), *statuses]:
        params = request.GET.copy()
        params.pop('page', None)
        if key:
            params['status'] = key
        else:
            params.pop('status', None)
        status_filters.append({
            'label': label,
            'url': f'?{params.urlencode()}',
            'is_current': request.GET.get('status', '') == key,
        })

    status_filter = request.GET.get('status', '')
    if status_filter in dict(Project.STATUS_CHOICES):
        queryset = queryset.filter(status=status_filter)
    else:
        status_filter = ''

    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(summary__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()

    tech_filter = request.GET.get('tech', '')
    if tech_filter in tags:
        queryset = queryset.filter(tags__name=tech_filter)
    else:
        tech_filter = ''

    page_obj = Paginator(queryset, 12).get_page(request.GET.get('page'))
    pagination_pages = []
    for number in page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1): # type: ignore
        is_ellipsis = isinstance(number, str)
        params = request.GET.copy()
        params['page'] = number if not is_ellipsis else page_obj.number
        pagination_pages.append({
            'number': number,
            'url': f'?{params.urlencode()}',
            'is_current': number == page_obj.number,
            'is_ellipsis': is_ellipsis,
        })

    def page_url(number):
        params = request.GET.copy()
        params['page'] = number
        return f'?{params.urlencode()}'

    return {
        'projects': page_obj.object_list,
        'page_obj': page_obj,
        'pagination_pages': pagination_pages,
        'previous_url': page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'next_url': page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
        'statuses': statuses,
        'status_filters': status_filters,
        'all_tags': tags,
        'status_filter': status_filter,
        'search_query': search_query,
        'tech_filter': tech_filter,
    }


def projects(request):
    return render(request, 'projects/projects.html', _project_listing_context(request))


def detail(request, slug):
    project = get_object_or_404(_published().prefetch_related('features'), slug=slug)
    items = list(_published().values_list('slug', 'title'))
    idx = next((i for i, (s, _) in enumerate(items) if s == slug), 0)
    prev_p = items[idx - 1] if idx > 0 else None
    next_p = items[idx + 1] if idx < len(items) - 1 else None
    tag_names = [t.name for t in project.tags.all()] # type: ignore
    related = list(_published().exclude(pk=project.pk).filter(models.Q(tags__name__in=tag_names) | models.Q(kind=project.kind, case_study=True)).distinct()[:2])
    return render(request, 'projects/detail.html', {
        'project': project,
        'related': related,
        'prev_project': dict(slug=prev_p[0], title=prev_p[1].split(' — ')[0]) if prev_p else None,
        'next_project': dict(slug=next_p[0], title=next_p[1].split(' — ')[0]) if next_p else None,
    })
