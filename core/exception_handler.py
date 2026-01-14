import structlog
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

from core.views import is_localhost

logger = structlog.get_logger(__name__)


def _has_unique_error(exc):
    """Check if ValidationError has a unique constraint error in non_field_errors."""
    if not isinstance(exc, ValidationError):
        return False
    if not isinstance(exc.detail, dict):
        return False
    errors = exc.detail.get("non_field_errors")
    if isinstance(errors, list) and len(errors) > 0:
        if hasattr(errors[0], "code") and errors[0].code == "unique":
            return True
    return False


def custom_exception_handler(exc, context):

    if isinstance(exc, OSError):
        pass
    elif isinstance(exc, NotAuthenticated):
        pass
    elif isinstance(exc, NotFound):
        pass
    else:
        logger.error(exc, exc_info=True)

    # Call REST framework's default exception handler first
    # to get the standard error response.
    response = exception_handler(exc, context)

    # response == None is an exception not handled by the DRF framework in the call above
    if response is None:
        if isinstance(exc, IntegrityError):
            response = Response({"detail": "Database conflict"}, status=status.HTTP_409_CONFLICT)
        else:
            response = Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        set_rollback()

    if _has_unique_error(exc):
        response = Response({"detail": "The player selected has already signed up or is in the process of signing up"}, status=status.HTTP_409_CONFLICT)

    if len(exc.args) > 0 and exc.args[0] == "Invalid token.":
        logger.warning("Detected an invalid token: deleting cookie")
        response.delete_cookie(
            key = "access_token",
            path = "/",
            samesite = "Lax",
            domain = ".bhmc.org" if not is_localhost else None,
        )

    return response
