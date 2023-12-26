import structlog
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = structlog.get_logger()


def custom_exception_handler(exc, context):

    # Log the exception
    # 2023-11-14 12:33:33,026: Unauthorized: /auth/users/me/
    # 2023-11-14 19:49:53,670: Not Found: /robots.txt
    # 2023-11-15 02:37:30,651: Not Found: /robots.txt
    # 2023-11-15 04:19:34,753: OSError: write error
    # 2023-11-15 07:58:40,303: Not Found: /robots.txt
    # 2023-11-15 09:57:33,179: Not Found: /wp-login.php
    # 2023-11-15 16:58:10,185: Not Found: /robots.txt
    # 2023-11-15 20:26:39,458: Not Found: /robots.txt
    # 2023-11-16 03:00:35,533: OSError: write error
    # 2023-11-16 03:01:21,102: OSError: write error
    # 2023-11-16 03:01:21,242: OSError: write error
    # 2023-11-16 03:01:21,314: OSError: write error
    # 2023-11-16 04:54:46,744: Not Found: /robots.txt
    # 2023-11-16 07:17:34,943: Not Found: /robots.txt
    # 2023-11-16 08:48:26,956: Not Found: /wp-login.php
    # TODO: do not log OSErrors (This fails: exc.name != "OSError")
    # if  exc.status_code != 401:
    #     logger.error(exc, exc_info=True)
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

    return response
