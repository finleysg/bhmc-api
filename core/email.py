import os
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from templated_email import send_templated_mail
from templated_email import InlineImage

from core.models import SeasonSettings
from events.models import Event
from register.models import RegistrationSlot, Player, Registration

config = SeasonSettings.objects.current_settings()
sender_email = "BHMC<postmaster@bhmc.org>"
secretary_email = "secretary@bhmc.org"
treasurer_email = "treasurer@bhmc.org"
admin_email = "admin@bhmc.org"

logo_file = os.path.join(settings.BASE_DIR, 'templates/templated_email/logo.png')
with open(logo_file, 'rb') as logo:
    image = logo.read()
    inline_image = InlineImage(filename=logo_file, content=image)


def send_notification(payment, event_id):
    user = User.objects.get(pk=payment.user_id)
    registration = Registration.objects.get(event_id=event_id, user=user)

    if payment.notification_type == "R":
        send_returning_member_welcome(user)
    elif payment.notification_type == "N":
        player = Player.objects.get(email=user.email)
        send_new_member_welcome(user)
        send_new_member_notification(user, player, registration.notes)

    if payment.notification_type is not None:
        # TODO: confirmation
        pass


def send_new_member_welcome(user):
    send_templated_mail(
        template_name='welcome.html',
        from_email=sender_email,
        recipient_list=[user.email],
        context={
            'first_name': user.first_name,
            'year': config.year,
            'login_url': '{}/session/login'.format(config.website_url),
            'account_url': '{}/my-account'.format(config.website_url),
            'matchplay_url': '{}/match-play'.format(config.website_url),
            'logo_image': inline_image
        },
        template_suffix='html',
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_returning_member_welcome(user):
    send_templated_mail(
        template_name='welcome_back.html',
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
def send_event_confirmation(user, group, event, config):

    registrations = list(RegistrationSlot.objects.filter(registration_group=group))
    required_fees = get_required_fees(event, registrations)
    optional_fees = get_optional_fees(event, registrations)

    email_context = {
        'user_name': '{} {}'.format(user.first_name, user.last_name),
        'event_name': event.name,
        'event_date': event.start_date,
        'event_start': event.start_time,
        'event_hole': get_starting_hole(event, group),
        'required_fees': '${:,.2f}'.format(required_fees),
        'optional_fees': '${:,.2f}'.format(optional_fees),
        'transaction_fees': '${:,.2f}'.format(Decimal(str(group.payment_amount)) - (required_fees + optional_fees)),
        'total_fees': '${:,.2f}'.format(group.payment_amount),
        'payment_confirmation_code': group.payment_confirmation_code,
        'show_confirmation_code': True,
        'members': get_members(event, registrations),
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
    recipients = get_recipients(user, registrations)

    if len(recipients) > 0:
        send_templated_mail(
            template_name='registration_confirmation.html',
            from_email=sender_email,
            recipient_list=recipients,
            context=email_context,
            template_suffix='html',
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


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


def get_required_fees(event, registrations):
    fees = Decimal('0.0')
    for reg in registrations:
        if reg.member is not None:
            fees = fees + event.event_fee

    return fees


def get_optional_fees(event, registrations):
    fees = Decimal('0.0')
    for reg in registrations:
        if reg.member is not None:
            if reg.is_gross_skins_paid:
                fees = fees + event.skins_fee
            if reg.is_net_skins_paid:
                fees = fees + event.skins_fee
            if reg.is_greens_fee_paid:
                fees = fees + event.green_fee
            if reg.is_cart_fee_paid:
                fees = fees + event.cart_fee

    return fees


def get_members(event, registrations):
    members = []
    for reg in registrations:
        if reg.member is not None:
            members.append({
                'name': reg.member.member_name(),
                'email': reg.member.member_email(),
                'fees': get_fees(reg, event)
            })
    return members


def get_fees(registration, event):
    fees = [{
        'description': 'Event Fee',
        'amount': '${:,.2f}'.format(event.event_fee)
    }]
    if registration.is_gross_skins_paid:
        fees.append({
            'description': 'Gross Skins',
            'amount': '${:,.2f}'.format(event.skins_fee)
        })
    if registration.is_net_skins_paid:
        fees.append({
            'description': 'Net Skins',
            'amount': '${:,.2f}'.format(event.skins_fee)
        })
    if registration.is_greens_fee_paid:
        fees.append({
            'description': 'Green Fee',
            'amount': '${:,.2f}'.format(event.green_fee)
        })
    if registration.is_cart_fee_paid:
        fees.append({
            'description': 'Cart Fee',
            'amount': '${:,.2f}'.format(event.cart_fee)
        })
    return fees


def get_recipients(user, registrations):
    recipients = []
    for reg in registrations:
        if reg.member is not None and reg.member.has_email():
            if reg.member.id != user.member.id:
                recipients.append(reg.member.member_email())

    return recipients
