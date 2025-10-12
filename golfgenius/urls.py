from django.urls import path
from . import views

app_name = "golfgenius"

urlpatterns = [
    # Player sync endpoints
    path("sync-players/", views.sync_players, name="sync_players"),
    path(
        "sync-player/<int:player_id>/",
        views.sync_single_player,
        name="sync_single_player",
    ),
    path("sync-event/<int:event_id>/", views.sync_event, name="sync_single_event"),
]
