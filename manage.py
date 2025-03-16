#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bhmc.settings")

    from django.core.management import execute_from_command_line
    from django.conf import settings

    if settings.DEBUG:
        if os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN"):
            import ptvsd
            ptvsd.enable_attach(address=('0.0.0.0', 5000))
            sys.stdout.write("Attached remote debugger")

    execute_from_command_line(sys.argv)
