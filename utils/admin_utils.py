from django.contrib.admin.apps import AdminConfig
from django.contrib.admin.sites import AdminSite
from django.db.models.base import ModelBase


class CommonAdminSite(AdminSite):
    model_sequences = {}

    def register(self, model_or_iterable, admin_class=None, **options):
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        if admin_class and admin_class.list_display == '__all__' or options.get('list_display') == '__all__':
            options['list_display'] = [
                field.name for field in model_or_iterable[0]._meta.concrete_fields
            ]

        super().register(model_or_iterable, admin_class, **options)

        for model in model_or_iterable:
            app_label = model._meta.app_label
            object_name = model._meta.object_name
            self.model_sequences[(app_label, object_name)] = len(self.model_sequences)

    def _build_app_dict(self, request, label=None):
        app_dict = super()._build_app_dict(request, label)
        all_app_dict = {label: app_dict} if label else app_dict

        for app_label, app_detail in all_app_dict.items():
            app_detail['models'].sort(
                key=lambda model_dict: self.model_sequences[(app_label, model_dict['object_name'])]
            )
            for i, model_dict in enumerate(app_detail['models']):
                model_dict['name'] = '{:0>3}. {}'.format(i + 1, model_dict['name'])

        return app_dict


class CommonAdminConfig(AdminConfig):
    default_site = 'utils.admin_utils.CommonAdminSite'
