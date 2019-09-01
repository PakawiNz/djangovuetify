from enum import Enum
from types import DynamicClassAttribute
from typing import Type
from uuid import uuid4

from django import forms
from django.contrib.auth.models import User
from django.db import models, transaction
from django.forms import SelectMultiple, MultipleChoiceField
from django.utils import timezone
from django.utils.decorators import classproperty
from rest_framework.fields import get_attribute


class LabeledEnum(str, Enum):
    def __new__(cls, value):
        ignoring_value = str(uuid4())
        obj = super().__new__(cls, ignoring_value)
        obj.label = value
        obj._value_ = ignoring_value
        return obj

    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def get(cls, name):
        return cls.__members__.get(name)

    @property
    def text(self):
        return self.label or self.name

    @DynamicClassAttribute
    def value(self):
        """The value of the Enum member."""
        return self._name_

    def __str__(self):
        return self.name


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
        try:
            return self.enum(value)
        except:
            return super().to_python(value)

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

class _StatusField(EnumField):
    def __init__(self, *args, **kwargs):
        super(EnumField, self).__init__(choices=[('', '')], max_length=100, editable=False)

    @property
    def enum(self):
        try:
            return self.model.STATUS
        except AttributeError:
            return _DummyLabeledEnum


class _ActionPermission:
    def permit(self, instance, user) -> bool:
        raise NotImplementedError()

    def __and__(self, other):
        return _AND(self, other)

    def __or__(self, other):
        return _OR(self, other)


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


class ACTION_PERMISSION:
    class EVERYONE(_ActionPermission):
        def permit(self, instance, user):
            return True

    class LAST_DOER(_ActionPermission):
        def __init__(self, action):
            self.action = action

        def permit(self, instance, user):
            log = instance.actions.filter(action=self.action).last()
            return bool(log) and log.user == user

    class ATTRIBUTE(_ActionPermission):
        def __init__(self, name):
            self.name = name

        def permit(self, instance, user):
            expected_user = get_attribute(instance, self.name.split('.'))
            return user == expected_user

    class FUNCTION(_ActionPermission):
        def __init__(self, function):
            self.function = function

        def permit(self, instance, user):
            return self.function(instance, user)


class StatefulModel(CommonModel):
    class STATUS(LabeledEnum):
        DUMMY = ''

    class ACTION(LabeledEnum):
        DUMMY = ''

    TRANSITION = [
        (None, ACTION.DUMMY, STATUS.DUMMY),
        (STATUS.DUMMY, ACTION.DUMMY, STATUS.DUMMY),
    ]

    ACTIONS_PERMISSION = {}

    status = _StatusField()
    updated = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._internal_save = False

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self._internal_save:
            raise Exception('directly save is not allowed.')

        super().save()

    def internal_save(self):
        self._internal_save = True
        self.save()
        self._internal_save = False

    @classproperty
    def action_log_class(cls):
        class StateActionLog(models.Model):
            timestamp = models.DateTimeField(auto_now=True)
            stater = models.ForeignKey(cls, on_delete=models.CASCADE, related_name='actions')
            status = EnumField(cls.STATUS, null=True)
            user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='+')
            action = EnumField(cls.ACTION)

            class Meta:
                abstract = True

        return StateActionLog

    @classmethod
    def _get_transition_map(cls):
        if not hasattr(cls, '_TRANSITION'):
            cls._TRANSITION_MAP = {
                (current_status, action): next_status
                for current_status, action, next_status in
                cls.TRANSITION
            }

        return cls._TRANSITION_MAP

    @classmethod
    def _get_allowed_action_map(cls):
        if not hasattr(cls, '_ALLOWED_ACTIONS'):
            cls._ALLOWED_ACTIONS_MAP = {}
            for current_status, action, next_status in cls.TRANSITION:
                cls._ALLOWED_ACTIONS_MAP.setdefault(current_status, []).append(action)

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

    def get_allowed_actions(self):
        return self._get_allowed_action_map().get(self.status, [])

    def get_permitted_allowed_actions(self, user):
        model = self.__class__
        if not model.ACTIONS_PERMISSION:
            return self.get_allowed_actions()

        return [
            action
            for action in self.get_allowed_actions()
            if self.check_permitted_action(action, user)
        ]

    def check_allowed_action(self, action):
        return (self.status, action) in self._get_transition_map()

    def check_permitted_action(self, action, user):
        model = self.__class__
        permissions = model.ACTIONS_PERMISSION.get(action, [])
        for permission in permissions:
            if permission.permit(self, user):
                return True

        return False

    def transition(self, user, action, **options):
        transition_map = self._get_transition_map()
        if not (self.status, action) in transition_map:
            raise Exception('invalid action')

        self.user = user
        options['user'] = user
        options['old_status'] = self.status

        pre_function = getattr(self, 'pre_{}'.format(action.name.lower()), None)
        if callable(pre_function):
            pre_function(options)

        with transaction.atomic():
            old_status = self.status
            self.status = transition_map[(old_status, action)]
            self.updated = timezone.now()
            self.internal_save()
            options['log'] = self._create_log(old_status, user, action, options)
            options['new_status'] = self.status

        post_function = getattr(self, 'post_{}'.format(action.name.lower()), None)
        if callable(post_function):
            post_function(options)

        return options['log']
