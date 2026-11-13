from django.urls import path

from . import views

app_name = 'books'

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:slug>/download/', views.download, name='download'),
    path('<str:slug>/', views.detail, name='detail'),
]
