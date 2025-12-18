import os
import structlog

from django.conf import settings
from templated_email import send_templated_mail, InlineImage

from core.util import current_season
from payments.utils import *

logger = structlog.getLogger(__name__)

sender_email = "BHMC<postmaster@bhmc.org>"
secretary_email = "secretary@bhmc.org"
treasurer_email = "treasurer@bhmc.org"
admin_email = "admin@bhmc.org"

logo_file = os.path.join(settings.BASE_DIR, "templates/templated_email/logo.png")
with open(logo_file, "rb") as logo:
    image = logo.read()
    inline_image = InlineImage(filename=logo_file, content=image)


def send_payment_notification(payment, registration, player):
    user = payment.user
    event = payment.event
    logger.info("Running send_payment_notification", email=user.email, notification_type=payment.notification_type)

    if payment.notification_type == "R":
        send_member_welcome(user)
        send_has_notes_notification(user, event, registration.notes)
    elif payment.notification_type == "N":
        send_member_welcome(user)
        send_new_member_notification(user, player, registration.notes)
    elif payment.notification_type == "M":
        send_match_play_confirmation(user)
        send_has_notes_notification(user, event, registration.notes)
    elif payment.notification_type == "C":
        send_event_confirmation(user, event, registration, payment)
        send_has_notes_notification(user, event, registration.notes)
    elif payment.notification_type == "U":
        send_update_confirmation(user, event, registration, payment)


def send_member_welcome(user):
    send_templated_mail(
        template_name="welcome.html",
        from_email=sender_email,
        recipient_list=[user.email],
        context={
            "first_name": user.first_name,
            "year": current_season(),
            "account_url": "{}/my-account".format(settings.WEBSITE_URL),
            "matchplay_url": "{}/match-play".format(settings.WEBSITE_URL),
            "logo_image": inline_image
        },
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_new_member_notification(user, player, notes):
    send_templated_mail(
        template_name="new_member_notification",
        from_email=sender_email,
        recipient_list=[treasurer_email, secretary_email],
        context={
            "name": "{} {}".format(user.first_name, user.last_name),
            "email": user.email,
            "ghin": player.ghin,
            "notes": notes,
            "admin_url": "{}/admin/register/player/?q={}".format(settings.ADMIN_URL, user.email),
            "logo_image": inline_image
        },
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_has_notes_notification(user, event, notes):
    if notes is not None and notes != "":
        send_templated_mail(
            template_name="has_notes_notification",
            from_email=sender_email,
            recipient_list=[treasurer_email, secretary_email],
            context={
                "name": "{} {}".format(user.first_name, user.last_name),
                "email": user.email,
                "event": event.name,
                "notes": notes,
                "logo_image": inline_image
            },
            template_suffix="html",
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


def send_match_play_confirmation(user):
    send_templated_mail(
        template_name="match-play.html",
        from_email=sender_email,
        recipient_list=[user.email],
        context={
            "first_name": user.first_name,
            "year": current_season(),
            "matchplay_url": "{}/match-play".format(settings.WEBSITE_URL),
            "logo_image": inline_image
        },
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )


def send_event_confirmation(user, event, registration, payment):

    slots = registration.slots.all()
    payment_details = payment.payment_details.all()
    required_fees = get_required_fees(event, payment_details)
    optional_fees = get_optional_fees(event, payment_details)

    email_context = {
        "user_name": registration.signed_up_by,
        "event_name": event.name,
        "event_date": event.start_date,
        "event_hole_or_start": get_start(event, registration, slots[0]),
        "required_fees": "${:,.2f}".format(required_fees),
        "optional_fees": "${:,.2f}".format(optional_fees),
        "transaction_fees": "${:,.2f}".format(payment.transaction_fee),
        "total_fees": "${:,.2f}".format(payment.payment_amount),
        "payment_confirmation_code": payment.payment_code,
        "show_confirmation_code": True,
        "players": get_players(event, slots, payment_details),
        "event_url": get_event_url(settings.WEBSITE_URL, event),
        "logo_image": inline_image
    }

    send_templated_mail(
        template_name="registration_confirmation.html",
        from_email=sender_email,
        recipient_list=[user.email],
        context=email_context,
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )

    # remove payment conf code before sending the rest
    email_context["show_confirmation_code"] = False
    recipients = get_recipients(user, slots)

    if len(recipients) > 0:
        send_templated_mail(
            template_name="registration_confirmation.html",
            from_email=sender_email,
            recipient_list=recipients,
            context=email_context,
            template_suffix="html",
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


def send_update_confirmation(user, event, registration, payment):

    payment_details = payment.payment_details.all()
    required_fees = get_required_fees(event, payment_details)
    optional_fees = get_optional_fees(event, payment_details)
    slots = get_payment_slots(registration, payment_details)

    email_context = {
        "user_name": registration.signed_up_by,
        "event_name": event.name,
        "event_date": event.start_date,
        "event_hole_or_start": get_start(event, registration, slots[0]),
        "required_fees": "${:,.2f}".format(required_fees),
        "optional_fees": "${:,.2f}".format(optional_fees),
        "transaction_fees": "${:,.2f}".format(payment.transaction_fee),
        "total_fees": "${:,.2f}".format(payment.payment_amount),
        "payment_confirmation_code": payment.payment_code,
        "show_confirmation_code": True,
        "players": get_players(event, slots, payment_details),
        "event_url": get_event_url(settings.WEBSITE_URL, event),
        "logo_image": inline_image
    }

    send_templated_mail(
        template_name="registration_update.html",
        from_email=sender_email,
        recipient_list=[user.email],
        context=email_context,
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )

    # remove payment conf code before sending the rest
    email_context["show_confirmation_code"] = False
    recipients = get_recipients(user, slots)

    if len(recipients) > 0:
        send_templated_mail(
            template_name="registration_update.html",
            from_email=sender_email,
            recipient_list=recipients,
            context=email_context,
            template_suffix="html",
            headers={"Reply-To": "no-reply@bhmc.org"}
        )


def send_refund_notification(payment, refund):
    event = payment.event
    user = payment.user
    
    email_context = {
        "user_name": f"{user.first_name} {user.last_name}",
        "event_name": event.name,
        "event_date": event.start_date,
        "total_refund": "${:,.2f}".format(refund.refund_amount),
        "refund_confirmation_code": refund.refund_code,
        "event_url": get_event_url(settings.WEBSITE_URL, event),
        "logo_image": inline_image
    }

    send_templated_mail(
        template_name="refund_notification.html",
        from_email=sender_email,
        recipient_list=[user.email],
        context=email_context,
        template_suffix="html",
        headers={"Reply-To": "no-reply@bhmc.org"}
    )
