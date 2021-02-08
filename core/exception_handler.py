from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback
from sentry_sdk import capture_exception


def custom_exception_handler(exc, context):

    # Log the exception
    if exc is not OSError and exc is not NotAuthenticated:
        capture_exception(exc)

    # Call REST framework's default exception handler first
    # to get the standard error response.
    response = exception_handler(exc, context)

    # response == None is an exception not handled by the DRF framework in the call above
    if response is None:
        if isinstance(exc, IntegrityError):
            response = Response({"detail": "Database conflict"}, status=status.HTTP_409_CONFLICT)
        else:
            response = Response({'detail': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        set_rollback()

    return response
