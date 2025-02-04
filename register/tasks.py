import structlog

from celery import shared_task
from register.models import Registration

logger = structlog.getLogger(__name__)


@shared_task(bind=True)
def remove_expired_registrations(self):
    logger.info("Scheduled job: remove expired registrations")
    Registration.objects.remove_expired_registrations()
