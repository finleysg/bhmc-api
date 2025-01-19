from celery import shared_task


@shared_task(bind=True)
def debug_task(self):
    return{
        "result": f'Request: {self.request!r}'
    }
