from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('login/', views.DashLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/live/', views.live_api, name='live_api'),

    path('visitors/', views.visitors, name='visitors'),
    path('visitors/export.csv', views.visitors_export, name='visitors_export'),
    path('visitors/<int:pk>/', views.visitor_detail, name='visitor_detail'),

    path('messages/', views.messages_list, name='messages'),
    path('messages/read-all/', views.messages_mark_all, name='messages_mark_all'),
    path('messages/<int:pk>/', views.message_detail, name='message_detail'),
    path('messages/<int:pk>/<str:action>/', views.message_action, name='message_action'),

    path('subscribers/', views.subscribers, name='subscribers'),

    path('about-text/', views.singleton_edit, {'key': 'profile'}, name='profile'),
    path('site-settings/', views.singleton_edit, {'key': 'settings'}, name='settings'),
    path('account/', views.PasswordView.as_view(), name='account'),

    path('content/<str:key>/', views.resource_list, name='resource_list'),
    path('content/<str:key>/new/', views.resource_edit, name='resource_new'),
    path('content/<str:key>/reorder/', views.resource_reorder, name='resource_reorder'),
    path('content/<str:key>/<int:pk>/', views.resource_edit, name='resource_edit'),
    path('content/<str:key>/<int:pk>/delete/', views.resource_delete, name='resource_delete'),
    path('content/<str:key>/<int:pk>/toggle/<str:field>/', views.resource_toggle, name='resource_toggle'),
]
