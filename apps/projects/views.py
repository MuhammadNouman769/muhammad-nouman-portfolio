from django.db import models
from django.shortcuts import get_object_or_404, render

from .models import Project


def _published():
    return Project.objects.filter(published=True).prefetch_related('tags')


def case_studies():
    return Project.objects.filter(published=True, case_study=True).prefetch_related('tags', 'features').order_by('order_in_showcase', 'order', '-id')


def projects(request):
    items = list(_published())
    statuses = [(k, v) for k, v in Project.STATUS_CHOICES if any(p.status == k for p in items)]
    tags = sorted({t.name for p in items for t in p.tags.all()}, key=str.lower)
    return render(request, 'projects/projects.html', {'projects': items, 'statuses': statuses, 'all_tags': tags,
                                                     'case_studies': list(case_studies())})


def detail(request, slug):
    project = get_object_or_404(_published().prefetch_related('features'), slug=slug)
    items = list(_published().values_list('slug', 'title'))
    idx = next((i for i, (s, _) in enumerate(items) if s == slug), 0)
    prev_p = items[idx - 1] if idx > 0 else None
    next_p = items[idx + 1] if idx < len(items) - 1 else None
    tag_names = [t.name for t in project.tags.all()]
    related = list(_published().exclude(pk=project.pk).filter(models.Q(tags__name__in=tag_names) | models.Q(kind=project.kind, case_study=True)).distinct()[:2])
    return render(request, 'projects/detail.html', {
        'project': project,
        'related': related,
        'prev_project': dict(slug=prev_p[0], title=prev_p[1].split(' — ')[0]) if prev_p else None,
        'next_project': dict(slug=next_p[0], title=next_p[1].split(' — ')[0]) if next_p else None,
    })
