from django.urls import path
from . import views

app_name = 'golfgenius'

urlpatterns = [
    # Player sync endpoints
    path('sync-players/', views.sync_players, name='sync_players'),
    path('sync-player/<int:player_id>/', views.sync_single_player, name='sync_single_player'),
    path('sync-status/', views.sync_status, name='sync_status'),
    
    # Golf Genius API info and testing
    path('test-connection/', views.test_connection, name='test_connection'),
    path('info/', views.golf_genius_info, name='golf_genius_info'),
]