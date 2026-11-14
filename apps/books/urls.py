from django.urls import path

from . import views

app_name = 'books'

urlpatterns = [
    path('', views.index, name='index'),
    path('<slug:slug>/', views.detail, name='detail'),
    path('<slug:slug>/read/', views.read, name='read'),
    path('<slug:slug>/file/', views.file, name='file'),
    path('<slug:slug>/download/', views.download, name='download'),
]
