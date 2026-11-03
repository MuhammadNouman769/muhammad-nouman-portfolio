from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
    path('health/', views.health, name='health'),
    path(settings.DASHBOARD_URL, include('apps.dashboard.urls')),
    path('', include('apps.home.urls')),
    path('about/', include('apps.about.urls')),
    path('experience/', include('apps.experience.urls')),
    path('projects/', include('apps.projects.urls')),
    path('blog/', include('apps.blog.urls')),
    path('services/', include('apps.services.urls')),
    path('skills/', include('apps.skills.urls')),
    path('contact/', include('apps.contact.urls')),
    path('privacy/', TemplateView.as_view(template_name='privacy.html'), name='privacy'),
]

if settings.ENABLE_DJANGO_ADMIN:
    urlpatterns.insert(0, path(settings.DJANGO_ADMIN_URL, admin.site.urls))

handler404 = 'core.views.page_not_found'
handler500 = 'core.views.server_error'

# Uploaded media. Fine for a portfolio; for heavy traffic let nginx serve /media/ directly (see deploy/).
urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]
