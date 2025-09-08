from datetime import date
from decimal import Decimal
from celery import shared_task
from django.db.models import Sum
from .models import SkinTransaction, Skin, SkinSettings
from register.models import Player

@shared_task
def generate_scheduled_payments(payment_date_str):
    """
    Generate scheduled payments for a given date.
    
    Args:
        payment_date_str (str): Date string in YYYY-MM-DD format
        
    For payments on the 1st: include Bi-Monthly and Monthly players
    For payments on the 15th: include only Bi-Monthly players
    For end of season (October 1): include all players
    """
    payment_date = date.fromisoformat(payment_date_str)
    day = payment_date.day
    month = payment_date.month
    
    # Determine which players to include based on the date
    if month == 10 and day == 1:
        # End of season - include all players
        eligible_settings = SkinSettings.objects.all()
    elif day == 1:
        # First of month - include Bi-Monthly and Monthly
        eligible_settings = SkinSettings.objects.filter(
            payment_frequency__in=['Bi-Monthly', 'Monthly']
        )
    elif day == 15:
        # Fifteenth of month - include only Bi-Monthly
        eligible_settings = SkinSettings.objects.filter(
            payment_frequency='Bi-Monthly'
        )
    else:
        # Invalid date for scheduled payments
        return {
            'status': 'error',
            'message': f'Invalid payment date: {payment_date_str}. Must be 1st, 15th, or October 1st.'
        }
    
    payments_created = 0
    total_amount = Decimal('0.00')
    
    for settings in eligible_settings:
        player = settings.player
        
        # Calculate unpaid balance
        total_skins = Skin.objects.filter(player=player).aggregate(
            total=Sum('skin_amount'))['total'] or Decimal('0.00')
        
        total_paid = SkinTransaction.objects.filter(
            player=player,
            direction='Outbound'
        ).aggregate(total=Sum('transaction_amount'))['total'] or Decimal('0.00')
        
        unpaid_balance = total_skins - total_paid
        
        # Create transaction if amount > 0
        if unpaid_balance > 0:
            SkinTransaction.objects.create(
                player=player,
                season=payment_date.year,  # Use current year as season
                transaction_type='Scheduled Payment',
                transaction_amount=unpaid_balance,
                transaction_date=payment_date,
                direction='Outbound'
            )
            payments_created += 1
            total_amount += unpaid_balance
    
    return {
        'status': 'success',
        'payment_date': payment_date_str,
        'payments_created': payments_created,
        'total_amount': str(total_amount),
        'eligible_players': eligible_settings.count()
    }
