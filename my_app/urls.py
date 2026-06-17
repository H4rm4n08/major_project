from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('live/', views.live_scores_view, name='live_scores'),
    path('fixtures/', views.fixtures_view, name='fixtures'),
    path('players/', views.player_search_view, name='player_search'),
    path('players/<str:player_id>/', views.player_stats_view, name='player_stats'),
]
