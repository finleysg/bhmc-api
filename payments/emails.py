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
    """
    Dispatches and sends the appropriate payment-related notification emails based on the payment's notification_type.
    
    Behavior by notification_type:
    - "R": send member welcome and, if present, a notes notification for the event.
    - "N": send member welcome and a new-member notification including player details.
    - "M": send match-play confirmation and, if present, a notes notification for the event.
    - "C": send event registration confirmation and, if present, a notes notification for the event.
    - "U": send a registration update confirmation.
    
    Parameters:
        payment: Payment object containing at least `user`, `event`, and `notification_type`.
        registration: Registration object (provides `notes` and slot information used by some notifications).
        player: Player object associated with the user; used when composing new-member notifications.
    """
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
    """
    Send a welcome email to a user containing account and match-play links and the club logo.
    
    Parameters:
        user (User): The user who will receive the welcome email; the user's email and first name are used in the message.
    """
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

    """
    Send registration confirmation emails for an event to the registrant and relevant recipients.
    
    Sends a confirmation email to the registrant containing event, player and payment details (including the payment confirmation code). Then resends the same confirmation with the confirmation code hidden to additional recipients derived from the registration (for example event administrators or teammates), if any.
    
    Parameters:
        user (User): The user who initiated the action (email recipient for the primary message).
        event (Event): The event for which the registration was made.
        registration (Registration): The registration containing slots, the signer name, and related metadata.
        payment (Payment): The payment record containing amounts, fees, payment code, and payment details.
    """
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

    """
    Send an email to the registrant and related recipients notifying them of an updated event registration.
    
    Builds an email context from the registration, payment, and event (fees, players, start info, confirmation code, links, and logo), sends a registration update email to the user's email address including the confirmation code, then sends the same email without the confirmation code to additional recipients derived from the registration slots.
    
    Parameters:
    	user (User): The user who owns the account/address to receive the primary email.
    	event (Event): The event whose registration was updated.
    	registration (Registration): The registration record containing slots and signer information.
    	payment (Payment): The payment associated with the registration (used for fees, transaction fee, and confirmation code).
    """
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
    """
    Notify a user by email about a processed refund for their event registration.
    
    The email contains the event name and date, the formatted refund amount, the refund confirmation code, a link to the event, and the inline logo image.
    
    Parameters:
        payment (Payment): The payment record associated with the refunded registration; provides event and user.
        refund (Refund): The refund record containing `refund_amount` and `refund_code`.
    """
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