from django.urls import path

from . import views

app_name = 'chatbot'

urlpatterns = [
    path('answer/', views.answer, name='answer'),
]
