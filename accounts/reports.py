from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SkinTransaction

class SkinReportViewSet(viewsets.ViewSet):
    """
    ViewSet for skins-related reports
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def payment_summary(self, request):
        """
        Skins Payment Report
        Returns a summary of all outbound transactions where the transaction type 
        is "Scheduled Payment" for a given date.
        
        Query params:
        - payment_date: Date in YYYY-MM-DD format (required)
        """
        payment_date = request.query_params.get('payment_date', None)
        if payment_date is None:
            return Response(
                {"error": "payment_date parameter is required (YYYY-MM-DD format)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get all scheduled payments for the specified date
            transactions = SkinTransaction.objects.filter(
                transaction_type='Scheduled Payment',
                direction='Outbound',
                transaction_date=payment_date
            ).select_related('player').order_by('player__last_name', 'player__first_name')

            # Format the response data
            report_data = []
            for transaction in transactions:
                report_data.append({
                    'player_name': f"{transaction.player.first_name} {transaction.player.last_name}",
                    'player_ghin': transaction.player.ghin,
                    'scheduled_payment_date': transaction.transaction_date,
                    'amount': transaction.transaction_amount
                })

            # Calculate totals
            total_amount = sum(item['amount'] for item in report_data)
            total_players = len(report_data)

            return Response({
                'payment_date': payment_date,
                'total_players': total_players,
                'total_amount': total_amount,
                'payments': report_data
            })

        except Exception as e:
            return Response(
                {"error": f"Error generating report: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def player_balance_summary(self, request):
        """
        Player Balance Summary Report
        Returns balance information for all players or a specific player
        
        Query params:
        - player_id: Optional player ID to filter by specific player
        - season: Optional season to filter skins by
        """
        from django.db.models import Sum
        from .models import Skin

        player_id = request.query_params.get('player_id', None)
        season = request.query_params.get('season', None)

        # Base querysets
        skins_qs = Skin.objects.all()
        transactions_qs = SkinTransaction.objects.filter(direction='Outbound')

        if player_id:
            skins_qs = skins_qs.filter(player_id=player_id)
            transactions_qs = transactions_qs.filter(player_id=player_id)

        if season:
            skins_qs = skins_qs.filter(event__season=season)
            transactions_qs = transactions_qs.filter(season=season)

        # Get unique players from skins
        players_with_skins = skins_qs.values_list('player', flat=True).distinct()
        
        report_data = []
        for player_id in players_with_skins:
            # Get player object
            from register.models import Player
            try:
                player = Player.objects.get(id=player_id)
            except Player.DoesNotExist:
                continue

            # Calculate totals for this player
            player_skins = skins_qs.filter(player_id=player_id)
            player_transactions = transactions_qs.filter(player_id=player_id)

            total_skins = player_skins.aggregate(total=Sum('skin_amount'))['total'] or 0
            total_paid = player_transactions.aggregate(total=Sum('transaction_amount'))['total'] or 0
            balance = total_skins - total_paid

            report_data.append({
                'player_id': player.id,
                'player_name': f"{player.first_name} {player.last_name}",
                'player_ghin': player.ghin,
                'total_skins_won': total_skins,
                'total_paid': total_paid,
                'current_balance': balance
            })

        # Sort by player name
        report_data.sort(key=lambda x: x['player_name'])

        return Response({
            'total_players': len(report_data),
            'players': report_data
        })
