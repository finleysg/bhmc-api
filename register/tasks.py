import structlog

from celery import shared_task
from register.models import Registration, RegistrationSlot

logger = structlog.getLogger(__name__)


@shared_task(bind=True)
def remove_expired_registrations(self):
    logger.info("Scheduled job: remove expired registrations")
    count = Registration.objects.clean_up_expired()
    return {
        "message": "Expired registrations removed",
        "count": count
    }

@shared_task(bind=True)
def remove_unused_registration_slots(self):
    logger.info("Scheduled job: remove unused registration slots")
    count = RegistrationSlot.objects.remove_unused_slots()
    return {
        "message": "Unused registration slots removed",
        "count": count
    }
