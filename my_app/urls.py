from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('squads/create/', views.squad_create_view, name='squad_create'),
    path('squads/<int:squad_id>/', views.squad_detail_view, name='squad_detail'),
    path('squads/<int:squad_id>/batting/', views.squad_batting_lineup_view, name='squad_batting_lineup'),
    path('squads/<int:squad_id>/slot/<int:slot>/', views.squad_slot_view, name='squad_slot'),
    path('squads/<int:squad_id>/bowling/', views.squad_bowling_lineup_view, name='squad_bowling_lineup'),
    path('squads/<int:squad_id>/bowling/slot/<int:slot>/', views.squad_bowling_slot_view, name='squad_bowling_slot'),
    path('squads/<int:squad_id>/fielding/', views.squad_fielding_view, name='squad_fielding'),
    path('squads/<int:squad_id>/fielding/slot/<int:slot>/', views.squad_fielding_slot_view, name='squad_fielding_slot'),
    path('squads/<int:squad_id>/coaches/', views.squad_coaches_view, name='squad_coaches'),
    path('squads/<int:squad_id>/coaches/<str:role>/', views.squad_coach_slot_view, name='squad_coach_slot'),
    path('live/', views.live_scores_view, name='live_scores'),
    path('fixtures/', views.fixtures_view, name='fixtures'),
    path('players/', views.player_search_view, name='player_search'),
    path('players/<str:player_id>/', views.player_stats_view, name='player_stats'),
]
