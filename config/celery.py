import logging
import os
import sys

from celery import Celery, shared_task
from celery.schedules import crontab
from celery.signals import after_setup_logger
from django.apps import AppConfig, apps
from django.conf import settings

from utils.format_utils import format_file_datetime

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')


class CeleryConfig(AppConfig):
    name = 'celery'
    verbose_name = 'Celery Config'

    def ready(self):
        app.config_from_object('django.conf:settings', namespace='CELERY')
        app.autodiscover_tasks([cfg.name for cfg in apps.get_app_configs()], force=True)
        app.conf.beat_schedule = {}
        for key, task in app.tasks.items():
            if getattr(task, 'beat_scheduling', None) is not None:
                app.conf.beat_schedule[key] = {
                    'task': '.'.join([task.__module__, task.__name__]),
                    'schedule': task.beat_scheduling
                }


@after_setup_logger.connect
def setup_loggers(*args, **kwargs):
    logger = logging.getLogger()
    formatter = logging.Formatter('[{asctime}: {levelname}/{processName}/{threadName}] {message}', style='{')

    datetime = format_file_datetime()
    date, time = datetime[:8], datetime[-6:]
    file_handler = logging.FileHandler(f'logs/celery-{sys.argv[3]}-{date}-{time}.log', 'a+', 'utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    print(f'REGISTERED NEW HANDLER: {str(file_handler)}')
    for handler in logger.handlers[:]:
        if handler is not file_handler and isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
            print(f'REMOVED OLD HANDLER: {str(handler)}')


def as_task(schedule=False, minute='*', hour='*', day_of_week='*', day_of_month='*', month_of_year='*', **kwargs):
    assert type(schedule) is bool, 'This decorator required initialized (need to be called)'

    def decorator(func):
        func = shared_task(func)
        if schedule:
            func.beat_scheduling = crontab(
                minute=minute,
                hour=hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                **kwargs
            )
        return func

    return decorator

# celery -A config worker -P gevent -l DEBUG -f logs/celery-worker.log
# celery -A config beat -l INFO -f logs/celery-beat.log
