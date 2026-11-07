from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.projects, name='projects'),
    path('case-studies/', views.case_studies_page, name='case_studies'),
    path('<slug:slug>/', views.detail, name='detail'),
]
