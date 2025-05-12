from celery import Celery

celery = Celery(
    'web_app',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1',
)

# щоб таски знайшлися
import tasks  # noqa

celery.autodiscover_tasks(['tasks'])
