from django.shortcuts import render

from apps.about.models import Profile
from apps.blog.models import Post
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.projects.views import case_studies
from apps.services.models import Service
from apps.skills.models import Skill, SkillCategory


def home(request):
    """Landing page: hero + highlights pulled live from the database."""
    published = Project.objects.filter(published=True)
    ticker = list(Skill.objects.values_list('name', flat=True)[:24])
    context = {
        'ticker': ticker,
        'profile': Profile.objects.first(),
        'case_studies': case_studies(),
        'latest_posts': Post.objects.filter(published=True).select_related('category')[:3],
        'experiences': Experience.objects.prefetch_related('highlights')[:2],
        'projects': published.filter(featured=True).prefetch_related('tags')[:4],
        'skill_categories': SkillCategory.objects.prefetch_related('skills')[:6],
        'services': Service.objects.all()[:8],
        'projects_count': published.count(),
        'live_projects_count': published.filter(status=Project.STATUS_LIVE).count(),
        'skills_count': Skill.objects.count(),
        'services_count': Service.objects.count(),
    }
    return render(request, 'home/home.html', context)
