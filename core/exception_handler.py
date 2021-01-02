from rest_framework.views import exception_handler, set_rollback
from sentry_sdk import capture_exception


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    # to get the standard error response.
    capture_exception(exc)
    response = exception_handler(exc, context)

    # response == None is an exception not handled by the DRF framework in the call above
    if response is None:
        set_rollback()

    return response
