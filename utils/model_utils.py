import re
from enum import Enum, _EnumDict, EnumMeta
from functools import lru_cache
from typing import Type

from django import forms
from django.contrib.auth.models import User
from django.db import models, transaction
from django.forms import SelectMultiple, MultipleChoiceField
from django.utils import timezone
from django.utils.functional import classproperty
from rest_framework.fields import get_attribute

REGEX_CONSTANCE = '[A-Z][A-Z0-9]*(_[A-Z0-9]+)*'


class _LabeledEnumMeta(EnumMeta):
    def __new__(metacls, cls, bases, classdict):
        for key in classdict:
            if re.match(f'^{REGEX_CONSTANCE}$', key):
                super(_EnumDict, classdict).__setitem__(key, (key, classdict[key]))
        return super().__new__(metacls, cls, bases, classdict)


class LabeledEnum(str, Enum, metaclass=_LabeledEnumMeta):
    """
    Enum which its value is its variable name and anything set will be stored in enum.label
    """

    def __new__(cls, value, label=''):
        obj = super().__new__(cls, value)
        obj._value_ = value
        if isinstance(label, dict):
            obj.label = label.pop('label', '')
            for k, v in label.items():
                setattr(obj, k, v)
        else:
            obj.label = label
        return obj

    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def get(cls, name):
        return cls.__members__.get(name)

    @property
    def text(self):
        return self.label or self.name

    def __str__(self):
        return self.value


# ============================================================================= HELPERS

class _DummyLabeledEnum(LabeledEnum):
    DUMMY = ''


class _EnumFormField(forms.TypedChoiceField):
    def prepare_value(self, value):
        if isinstance(value, Enum):
            return value.value
        else:
            return value


class _MultiEnumWidget(SelectMultiple):
    def format_value(self, value):
        return [str(getattr(v, 'value', v)) for v in value] if value else []


# ============================================================================= FIELDS

class EnumField(models.CharField):
    def __init__(self, enum: Type[LabeledEnum], **kwargs):
        assert issubclass(enum, LabeledEnum)
        self.enum = enum
        kwargs['choices'] = [(e.value, e.name) for e in enum]
        kwargs['max_length'] = 100
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if 'choices' in kwargs:
            kwargs.pop('choices')
            args = [_DummyLabeledEnum]
        if 'default' in kwargs:
            if isinstance(kwargs['default'], LabeledEnum):
                kwargs['default'] = kwargs['default'].value
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return value
        value = super().to_python(value)
        if self.enum:
            return self.enum.get(value)
        else:
            return value

    def get_db_prep_value(self, value, connection, prepared=False):
        value = super().get_db_prep_value(value, connection, prepared)
        if isinstance(value, LabeledEnum):
            return value.value
        return value

    def _get_flatchoices(self):
        """Django Amdin list_filter call this method for list of choices on the right"""
        return [(e.value, e.label or e.name) for e in self.enum]

    flatchoices = property(_get_flatchoices)

    def get_choices(self, include_blank=True, blank_choice=models.BLANK_CHOICE_DASH, limit_choices_to=None):
        """Choice for display in ComboBox by Django Admin form field

        we display both name and label to make it easier to understand"""
        first_choice = (blank_choice if include_blank else [])
        return first_choice + [(e.value, '%s - %s' % (e.name, e.label)) for e in self.enum]

    def formfield(self, **kwargs):
        default = {
            'choices_form_class': _EnumFormField,
        }
        default.update(kwargs)
        return super().formfield(**default)


class MultiEnumField(models.TextField):
    description = "String (up to %(max_length)s)"

    def __init__(self, enum: Type[LabeledEnum], **kwargs):
        assert issubclass(enum, LabeledEnum)
        self.enum = enum
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        args = [_DummyLabeledEnum]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return ''

        if type(value) is list:
            return [self.enum(str(value)) for value in value]

        if type(value) is str:
            return [self.enum(str(value)) for value in value.split(',')]

        raise Exception('invalid enum list')

    def get_prep_value(self, value):
        return ','.join(str(v.value) for v in value)

    def formfield(self, **kwargs):
        return MultipleChoiceField(
            choices=[(e.value, e.name) for e in self.enum],
            required=not self.blank,
            widget=_MultiEnumWidget,
        )

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))


# ============================================================================= MODELS

class CommonModelQuerySet(models.QuerySet):
    pass


class CommonModel(models.Model):
    objects = CommonModelQuerySet.as_manager()
    _meta = None

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.pre_save()
        super().save(force_insert, force_update, using, update_fields)
        self.post_save()

    def pre_save(self):
        pass

    def post_save(self):
        pass

    class Meta:
        abstract = True


class TransactionalModel(CommonModel):
    created_time = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', editable=False)
    updated_time = models.DateTimeField(auto_now=True, editable=False)
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', editable=False)

    class Meta:
        abstract = True


# ============================================================================= STATEFUL MODELS

class DirectlySaveException(Exception):
    pass


class InvalidActionException(Exception):
    pass


class _StatusField(EnumField):
    def __init__(self, *args, **kwargs):
        super(EnumField, self).__init__(choices=[('', '')], max_length=100, editable=False)

    @property
    def enum(self):
        try:
            return self.model.STATUS
        except AttributeError:
            return _DummyLabeledEnum


class ActionPermission:
    class _ActionPermission:
        def permit(self, instance, user) -> bool:
            raise NotImplementedError()

        def __and__(self, other):
            return ActionPermission._AND(self, other)

        def __or__(self, other):
            return ActionPermission._OR(self, other)

    class _AND(_ActionPermission):
        def __init__(self, *permissions):
            self.permissions = permissions

        def permit(self, instance, user):
            return all(permission.permit(instance, user) for permission in self.permissions)

    class _OR(_ActionPermission):
        def __init__(self, *permissions):
            self.permissions = permissions

        def permit(self, instance, user):
            return any(permission.permit(instance, user) for permission in self.permissions)

    class EVERYONE(_ActionPermission):
        def permit(self, instance, user):
            return True

    class LAST(_ActionPermission):
        def __init__(self, action):
            self.action = action

        def permit(self, instance, user):
            log = instance.actions.filter(action=self.action).last()
            return bool(log) and log.user == user

    class ATTR(_ActionPermission):
        def __init__(self, name):
            self.name = name

        def permit(self, instance, user):
            expected_user = get_attribute(instance, self.name.split('.'))
            return user == expected_user

    class PERM(_ActionPermission):
        def __init__(self, *permissions):
            """
            :param permissions:
                if single permission provided: it will give True if user has that permission.
                if multiple permission provided: it will give True if user has any of those permissions.
                if single list provided: it will give True if user has all of those permissions in that list.
                if multiple list provided: it will give True if user has all of those permissions in any of those list.
            :return:
            """
            self.permissions = permissions

        def permit(self, instance, user: User):
            for permission in self.permissions:
                if type(permission) is not list:
                    permission = [permission]
                if all(user.has_perm(perm) for perm in permission):
                    return True
            return False

    class FUNC(_ActionPermission):
        def __init__(self, function):
            self.function = function

        def permit(self, instance, user):
            return self.function(instance, user)


class StatefulModel(CommonModel):
    """StatefulModel is abstract model that use for state management on difference actions

    usage:

        To use this model, one have to specify class Status, Action , List of Transition and Actions_permission

    :Example:

    class A(StatefulModel)
        class STATUS(LabeledEnum):
            NEW = ''
            DRAFT = ''
            WAIT_FOR_APPROVE = ''
        class ACTION(LabeledEnum):
            NEW = ''
            SAVE = ''
            SUBMIT = ''
        TRANSITION = [
            (None, ACTION.NEW, STATUS.NEW),
            (STATUS.NEW, ACTION.SAVE, STATUS.DRAFT),
            (STATUS.NEW, ACTION.SUBMIT, STATUS.WAIT_FOR_APPROVE),]
        ACTIONS_PERMISSION = {
            ACTION.NEW: UserAccess.EVERY_ONE(),
            ACTION.SUBMIT: UserAccess.EVERY_ONE(),
            ACTION.DRAFT: UserAccess.ATTRIBUTE('owner'),}

    """

    class STATUS(LabeledEnum):
        DUMMY = ''

    class ACTION(LabeledEnum):
        DUMMY = ''

    TRANSITION = []

    ACTIONS_PERMISSION = {}

    status = _StatusField()
    actions: models.Manager

    class Meta:
        abstract = True

    # ============================================================================= internal function

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._internal_save = False

    @classmethod
    def _zip_current_and_next_status(cls, current_status, next_status):
        if current_status is cls.STATUS and next_status is cls.STATUS:
            return zip(cls.STATUS, cls.STATUS)
        if current_status is cls.STATUS:
            return ((s, next_status) for s in cls.STATUS)
        if next_status is cls.STATUS:
            return ((current_status, s) for s in cls.STATUS)
        return [(current_status, next_status)]

    @classmethod
    def _get_transition_map(cls):
        if not hasattr(cls, '_TRANSITION'):
            cls._TRANSITION_MAP = {k: v for k, v in ({
                (cs, action): ns
                for current_status, action, next_status in cls.TRANSITION
                for cs, ns in cls._zip_current_and_next_status(current_status, next_status)
            }).items() if v is not None}

        return cls._TRANSITION_MAP

    @classmethod
    def _get_allowed_action_map(cls):
        """use to get all actions of the application

        :return: dictionary of all actions with key current_status and the list of actions as structure below
            {None: [<ACTION.NEW: 1>], <STATUS.DRAFTED: 1>: [<ACTION.UPDATE: 2>, <ACTION.DELETE: 4>, <ACTION.CREATE: 24>, <ACTION.CANCEL: 5>],}
        """
        if not hasattr(cls, '_ALLOWED_ACTIONS_MAP'):
            cls._ALLOWED_ACTIONS_MAP = {}
            for current_status, action in cls._get_transition_map().keys():
                cls._ALLOWED_ACTIONS_MAP.setdefault(current_status, []).append(action)

            actions_index = {action: i for i, action in enumerate(cls.ACTION)}
            for actions in cls._ALLOWED_ACTIONS_MAP.values():
                actions.sort(key=actions_index.get)

        return cls._ALLOWED_ACTIONS_MAP

    def _create_log(self, status, user, action, options):
        log = self.actions.model(
            stater=self,
            status=status,
            user=user,
            action=action,
        )

        fields = {field.name for field in self.actions.model._meta.local_concrete_fields}
        fields = fields.difference({'id', 'timestamp', 'stater', 'status', 'user', 'action'})
        for key, value in options.items():
            if key in fields:
                setattr(log, key, value)

        log.save()
        return log

    # ============================================================================= class creation function

    @classproperty
    def action_log_class(cls):
        class StateActionLog(CommonModel):
            timestamp = models.DateTimeField(auto_now=True)
            stater = models.ForeignKey(cls, on_delete=models.CASCADE, related_name='actions')
            status = EnumField(cls.STATUS, null=True)
            user = models.ForeignKey(User, models.PROTECT, related_name='+')
            action = EnumField(cls.ACTION)

            class Meta:
                abstract = True

        return StateActionLog

    # ============================================================================= selecting function

    @classproperty
    def action_log_model(cls):
        return cls.actions.field.model

    @classmethod
    def get_actionable_statuses(cls, checking_action):
        return [status for status, action in cls._get_transition_map().keys() if action is checking_action]

    def get_allowed_actions(self):
        """use to get all actions on current status

        :return: list of actions for the current status as structure below
            [<ACTION.UPDATE: 2>, <ACTION.DELETE: 4>, <ACTION.CREATE: 24>, <ACTION.CANCEL: 5>]
        """
        return self._get_allowed_action_map().get(self.status or None, [])

    def get_permitted_allowed_actions(self, user):
        """use to get all permit actions on specify user

        :param user: user instance to validate permit action
        :type user: :class:`django.contrib.auth.models.User`
        :return: list of all actions that user has the permission as structure below
            [<ACTION.UPDATE: 2>,<ACTION.CANCEL: 5>]
        """
        model = self.__class__
        if not model.ACTIONS_PERMISSION:
            return self.get_allowed_actions()

        return [
            action
            for action in self.get_allowed_actions()
            if self.check_permitted_action(action, user)
        ]

    def check_allowed_action(self, action):
        """use to check whether specify action is allowed for current status or not

        :param action: action to check whether is allow for current status
        :type action: :class:`Enum`
        :return: true if current_status and action is in the transition_map otherwise return false
        """
        return (self.status or None, action) in self._get_transition_map()

    def check_permitted_action(self, action, user):
        """use to check permit action on user

        :param action: enum action to check for permit
        :type action: :class:`Enum`
        :param user: user instance to check for permit
        :type user: :class:`django.contrib.auth.models.User`
        :return: true if user has the permission on this action otherwise return false
        """
        model = self.__class__
        if not model.ACTIONS_PERMISSION:
            return True

        permission = model.ACTIONS_PERMISSION.get(action)
        if permission and permission.permit(self, user):
            return True

        return False

    def check_permitted_allowed_action(self, action, user):
        return self.check_allowed_action(action) and self.check_permitted_action(action, user)

    # ============================================================================= updating function

    @transaction.atomic
    def transition(self, user, action, **options):
        """use to transition from one status to another status with curtain action

        :param user: user instance that perform on curtain action
        :type user: :class:`django.contrib.auth.models.User`
        :param action: enum action was performed
        :type action: :class:`Enum`
        :param options: keyword arguments for the transitions
        :return: log object
        """
        old_status = self.status or None
        transition_map = self._get_transition_map()
        if not (old_status, action) in transition_map:
            raise InvalidActionException(type(self), self.pk, old_status, action)

        options['user'] = user
        options['old_status'] = old_status

        pre_function = getattr(self, 'pre_{}'.format(action.name.lower()), None)
        if callable(pre_function):
            pre_function(options)

        self.status = transition_map[(old_status, action)]
        self.updated = timezone.now()
        self.internal_save()
        options['log'] = self._create_log(old_status, user, action, options)
        options['new_status'] = self.status

        post_function = getattr(self, 'post_{}'.format(action.name.lower()), None)
        if callable(post_function):
            post_function(options)

        return options['log']

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self._internal_save:
            raise DirectlySaveException('directly save is not allowed.')

        super().save()

    def internal_save(self):
        """
        To control the save process for StateFulModel by prevented StateFulModel from directly save
        """
        self._internal_save = True
        self.save()
        self._internal_save = False

    # =============================================================================


# ============================================================================= useful utils

@lru_cache(1)
def get_system_user():
    return User.objects.get_or_create(username='system', defaults=dict(first_name='System', last_name='System', is_superuser=True))[0]


def get_primitive_fields_name(model, *exclude):
    return [
        field.name for field in model._meta.get_fields()
        if field.name not in exclude and not isinstance(field, (models.ManyToManyField, models.ManyToOneRel, models.ManyToManyRel))
    ]
