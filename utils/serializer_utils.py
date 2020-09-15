from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from utils.model_utils import StatefulModel


class ActionField(serializers.Field):
    def get_attribute(self, instance):
        raise serializers.SkipField()

    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        action = self.parent.Meta.model.ACTION.get(data)
        if not action:
            raise ValidationError('"{}" is not a valid action.'.format(data))

        instance = self.parent.instance
        if instance and not instance.check_allowed_action(action):
            raise ValidationError('"{}" action is not allowed.'.format(data))

        if instance and not instance.check_permitted_action(action, self.context['request'].user):
            raise ValidationError('"{}" action is not permitted.'.format(data))

        return action


class AutoUserField(serializers.Field):
    def __init__(self):
        super().__init__(default=None, allow_null=True)

    def get_value(self, dictionary):
        return self.context['request'].user

    def to_internal_value(self, data):
        return data

    def get_attribute(self, instance):
        return super().get_attribute(instance)

    def to_representation(self, value):
        return value.username


class AllowedActionsField(serializers.Field):
    def __init__(self):
        super().__init__(source='*', read_only=True)

    def to_representation(self, instance: StatefulModel):
        return [action.name for action in instance.get_permitted_allowed_actions(self.context['request'].user)]


class EnumField(serializers.Field):
    def __init__(self, enum, **kwargs):
        self.enum = enum
        super().__init__(**kwargs)

    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        enum = self.enum.get(data)
        if not enum:
            raise ValidationError('"{}" is not a valid enum.'.format(data))
        return enum


class CommonModelSerializer(serializers.ModelSerializer):
    @property
    def user(self):
        return self.context['request'].user


class StatefulSerializer(serializers.ModelSerializer):
    action = ActionField()
    status = serializers.CharField(source='status.name', read_only=True)
    allowed_actions = AllowedActionsField()

    def validate_action(self, action):
        self.context['action'] = action
        return action

    @staticmethod
    def required_action(validate_method):
        def inner_validate_method(self, value):
            if 'action' not in self.context:
                raise serializers.SkipField()

            return validate_method(self, value, self.context['action'])

        return inner_validate_method

    class Meta:
        abstract = True
        fields = ['action', 'status', 'allowed_actions']


def get_all_field_serializer(model):
    _model = model

    class AllFieldCommonModelSerializer(CommonModelSerializer):
        class Meta:
            model = _model
            fields = '__all__'

    return AllFieldCommonModelSerializer
