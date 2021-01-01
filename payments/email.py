import os
from decimal import Decimal
from django.conf import settings
from templated_email import send_templated_mail, InlineImage

from core.models import SeasonSettings

config = SeasonSettings.objects.current_settings()
sender_email = "BHMC<postmaster@bhmc.org>"
secretary_email = "secretary@bhmc.org"
treasurer_email = "treasurer@bhmc.org"
admin_email = "admin@bhmc.org"

logo_file = os.path.join(settings.BASE_DIR, 'templates/templated_email/logo.png')
with open(logo_file, 'rb') as logo:
    image = logo.read()
    inline_image = InlineImage(filename=logo_file, content=image)


def send_notification(payment, fees, slots, player):
    user = payment.user
    event = payment.event
    registration = slots[0].registration

    if payment.notification_type == "R":
        send_member_welcome(user)
    elif payment.notification_type == "N":
        send_member_welcome(user)
        send_new_member_notification(user, player, registration.notes)
    elif payment.notification_type == "C":
        # TODO: confirmation
        pass

    if registration.notes is not None:
        send_has_notes_notification(user, event, registration.notes)


def send_member_welcome(user):
    send_templated_mail(
        template_name='welcome.html',
        from_email=sender_email,
        recipient_list=[user.email],
        context={
            'first_name': user.first_name,
            'year': config.year,
            'account_url': '{}/my-account'.format(config.website_url),
            'matchplay_url': '{}/match-play'.format(config.website_url),
            'logo_image': inline_image
        },
        template_suffix='html',
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_new_member_notification(user, player, notes):
    send_templated_mail(
        template_name='new_member_notification',
        from_email=sender_email,
        recipient_list=[treasurer_email, secretary_email],
        context={
            'name': '{} {}'.format(user.first_name, user.last_name),
            'email': user.email,
            'ghin': player.ghin,
            'notes': notes,
            'admin_url': '{}/admin/auth/user/?q={}'.format(config.admin_url, user.username),
            'logo_image': inline_image
        },
        template_suffix='html',
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_has_notes_notification(user, event, notes):
    if notes is not None and notes != '':
        send_templated_mail(
            template_name='has_notes_notification',
            from_email=sender_email,
            recipient_list=[treasurer_email, secretary_email],
            context={
                'name': '{} {}'.format(user.first_name, user.last_name),
                'email': user.email,
                'event': event.name,
                'notes': notes,
                'logo_image': inline_image
            },
            template_suffix='html',
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


# TODO: needs rework based on scheema changes
def send_event_confirmation(user, event, registration, slots, payment, fees):

    required_fees = get_required_fees(event, fees)
    optional_fees = get_optional_fees(event, fees)

    email_context = {
        'user_name': '{} {}'.format(user.first_name, user.last_name),
        'event_name': event.name,
        'event_date': event.start_date,
        'event_start': event.start_time,
        'event_hole': get_starting_hole(event, registration),
        'required_fees': '${:,.2f}'.format(required_fees),
        'optional_fees': '${:,.2f}'.format(optional_fees),
        'transaction_fees': '${:,.2f}'.format(payment.transaction_fee),
        'total_fees': '${:,.2f}'.format(payment.payment_amount),
        'payment_confirmation_code': payment.payment_code,
        'show_confirmation_code': True,
        'players': get_players(event, slots, fees),
        'event_url': '{}/events/{}/detail'.format(config.website_url, event.id),
        'logo_image': inline_image
    }

    send_templated_mail(
        template_name='registration_confirmation.html',
        from_email=sender_email,
        recipient_list=[user.email],
        context=email_context,
        template_suffix='html',
        headers={"Reply-To": "no-reply@bhmc.org"}
    )

    # remove payment conf code before sending the rest
    email_context['show_confirmation_code'] = False
    recipients = get_recipients(user, slots)

    if len(recipients) > 0:
        send_templated_mail(
            template_name='registration_confirmation.html',
            from_email=sender_email,
            recipient_list=recipients,
            context=email_context,
            template_suffix='html',
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


# TODO: based on start time and start type
def get_starting_hole(event, group):
    if event.event_type == 'L':
        course_name = group.course_setup.name.replace(' League', '')
        if group.starting_hole == 1:
            if group.starting_order == 0:
                return '{} 3:00 pm'.format(course_name)
            else:
                return '{} 3:09 pm'.format(course_name)
        elif group.starting_hole == 2:
            if group.starting_order == 0:
                return '{} 3:18 pm'.format(course_name)
            else:
                return '{} 3:27 pm'.format(course_name)
        elif group.starting_hole == 3:
            if group.starting_order == 0:
                return '{} 3:36 pm'.format(course_name)
            else:
                return '{} 3:45 pm'.format(course_name)
        elif group.starting_hole == 4:
            if group.starting_order == 0:
                return '{} 3:54 pm'.format(course_name)
            else:
                return '{} 4:03 pm'.format(course_name)
        elif group.starting_hole == 5:
            if group.starting_order == 0:
                return '{} 4:12 pm'.format(course_name)
            else:
                return '{} 4:21 pm'.format(course_name)
        elif group.starting_hole == 6:
            if group.starting_order == 0:
                return '{} 4:30 pm'.format(course_name)
            else:
                return '{} 4:39 pm'.format(course_name)
        elif group.starting_hole == 7:
            if group.starting_order == 0:
                return '{} 4:48 pm'.format(course_name)
            else:
                return '{} 4:57 pm'.format(course_name)
        elif group.starting_hole == 8:
            if group.starting_order == 0:
                return '{} 5:06 pm'.format(course_name)
            else:
                return '{} 5:15 pm'.format(course_name)
        elif group.starting_hole == 9:
            if group.starting_order == 0:
                return '{} 5:24 pm'.format(course_name)
            else:
                return '{} 5:33 pm'.format(course_name)

    return 'Tee times'


def zget_starting_hole(event, group):
    if event.event_type == 'L':
        course_name = group.course_setup.name.replace(' League', '')
        if group.starting_order == 0:
            return '{} {}A'.format(course_name, group.starting_hole)
        else:
            return '{} {}B'.format(course_name, group.starting_hole)

    return 'Tee times'


def get_required_fees(event, fees):
    required = Decimal('0.0')
    for fee in fees:
        event_fee = next((f for f in event.fees if f == fee.event_fee), None)
        if event_fee.is_required:
            required = required + event.event_fee.amount

    return required


def get_optional_fees(event, fees):
    optional = Decimal('0.0')
    for fee in fees:
        event_fee = next((f for f in event.fees if f == fee.event_fee), None)
        if not event_fee.is_required:
            optional = optional + event.event_fee.amount

    return optional


def get_players(event, slots, fees):
    players = []
    for slot in slots:
        if slot.player is not None:
            players.append({
                'name': slot.player.player_name(),
                'email': slot.player.email,
                'fees': get_fees(event, filter(lambda fee: fee.registration_slot == slot, fees))
            })
    return players


def get_fees(event, fees):
    player_fees = []
    for fee in fees:
        event_fee = next((f for f in event.fees if f == fee.event_fee), None)
        player_fees.append({
            "description": event_fee.fee_type.name,
            "amount": "${:,.2f}".format(event_fee.amount)
        })
    return player_fees


# Get emails for the rest of the group
def get_recipients(user, slots):
    recipients = []
    for slot in slots:
        if slot.player is not None and slot.player.user_id != user.id:
            recipients.append(slot.player.email)

    return recipients
