import re
from enum import Enum

REGEX_CODENAME = '^(can|is|has)_[a-z][a-z0-9]*(_[a-z0-9]+)*$'


class PermissionEnum(str, Enum):
    """
    Enum for permission use in Djaks Frameworks
    """

    def __new__(cls, value, description=''):
        if not re.match(REGEX_CODENAME, value):
            raise Exception('invalid codename format')

        obj = super().__new__(cls, value)
        obj._value_ = '{}.{}'.format(cls.__module__.split('.')[-2], value)
        obj.codename = value
        obj.description = description or value.capitalize().replace('_', ' ')
        return obj

    def __str__(self):
        return self.value

    @property
    def meta(self):
        return (self.codename, self.description)

    @classmethod
    def get_permissions_meta(cls):
        return [e.meta for e in cls]
