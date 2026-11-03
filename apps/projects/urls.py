from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.projects, name='projects'),
    path('<slug:slug>/', views.detail, name='detail'),
]
