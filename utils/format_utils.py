import datetime
import re
from decimal import Decimal

from django.utils import timezone

ACCEPTED_DATE_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%f%z',
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%d',
]


def trying(func, default):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return default

    return inner


def camel(snake):
    return ''.join(map(str.title, snake.split('_')))


def parse_int(value):
    try:
        return int(value)
    except:
        pass


def parse_decimal(value, default=Decimal('0')):
    try:
        if isinstance(value, (float, int)):
            value = '{:.2f}'.format(value)
        else:
            value = re.sub('[^\d.]', '', value)
        return Decimal(value).quantize(Decimal('0.01'))
    except:
        return default


def parse_datetime(value):
    try_parse = trying(datetime.datetime.strptime, None)
    return next((result for result in (try_parse(value, format) for format in ACCEPTED_DATE_FORMATS) if result), None)


def parse_date(value):
    value = parse_datetime(value)
    return value and value.date()


def format_iso_datetime(value: datetime.date = None):
    if value is None:
        value = timezone.now()
    value = trying(getattr(value, 'astimezone', None), value)()
    return value.strftime('%Y-%m-%d %H:%M:%S')


def format_iso_date(value: datetime.date = None):
    if value is None:
        value = timezone.now()
    value = trying(getattr(value, 'astimezone', None), value)()
    return value.strftime('%Y-%m-%d')


def format_file_date(value: datetime.datetime = None):
    if value is None:
        value = timezone.now()
    value = trying(getattr(value, 'astimezone', None), value)()
    return value.strftime('%Y%m%d')


def format_file_datetime(value: datetime.datetime = None):
    if value is None:
        value = timezone.now()
    value = trying(getattr(value, 'astimezone', None), value)()
    return value.strftime('%Y%m%d_%H%M%S')
