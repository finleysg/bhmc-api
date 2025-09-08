from django.db.models import Sum, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SkinTransaction, Skin, SkinSettings
from .serializers import (
    SkinTransactionSerializer, SkinSerializer, SkinSettingsSerializer,
    SimpleSkinSerializer, SimpleSkinTransactionSerializer
)

class SkinTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = SkinTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by player and optionally by season"""
        queryset = SkinTransaction.objects.all()
        player_id = self.request.query_params.get('player_id', None)
        season = self.request.query_params.get('season', None)

        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)
        if season is not None:
            queryset = queryset.filter(season=season)

        return queryset.order_by('-transaction_date', '-transaction_timestamp')

class SkinViewSet(viewsets.ModelViewSet):
    serializer_class = SkinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by player, season, or event"""
        queryset = Skin.objects.all()
        player_id = self.request.query_params.get('player_id', None)
        season = self.request.query_params.get('season', None)
        event_id = self.request.query_params.get('event_id', None)

        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)
        if season is not None:
            queryset = queryset.filter(event__season=season)
        if event_id is not None:
            queryset = queryset.filter(event_id=event_id)

        return queryset.order_by('-event__start_date', 'hole__hole_number')

    @action(detail=False, methods=['get'])
    def by_event(self, request):
        """Get skins won by event"""
        event_id = request.query_params.get('event_id', None)
        if event_id is None:
            return Response({"error": "event_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        skins = self.get_queryset().filter(event_id=event_id)
        serializer = self.get_serializer(skins, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unpaid_balance(self, request):
        """Get a player's current non-paid skins balance"""
        player_id = request.query_params.get('player_id', None)
        if player_id is None:
            return Response({"error": "player_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        # Calculate total skins won
        total_skins = Skin.objects.filter(player_id=player_id).aggregate(
            total=Sum('skin_amount'))['total'] or 0

        # Calculate total outbound payments
        total_paid = SkinTransaction.objects.filter(
            player_id=player_id, 
            direction='Outbound'
        ).aggregate(total=Sum('transaction_amount'))['total'] or 0

        balance = total_skins - total_paid

        return Response({
            "player_id": player_id,
            "total_skins_won": total_skins,
            "total_paid": total_paid,
            "unpaid_balance": balance
        })

class SkinSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = SkinSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter by player"""
        queryset = SkinSettings.objects.all()
        player_id = self.request.query_params.get('player_id', None)

        if player_id is not None:
            queryset = queryset.filter(player_id=player_id)

        return queryset

    @action(detail=False, methods=['get'])
    def by_player(self, request):
        """Get a player's skin settings"""
        player_id = request.query_params.get('player_id', None)
        if player_id is None:
            return Response({"error": "player_id parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            settings = SkinSettings.objects.get(player_id=player_id)
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except SkinSettings.DoesNotExist:
            return Response({"error": "Settings not found for this player"}, 
                          status=status.HTTP_404_NOT_FOUND)
