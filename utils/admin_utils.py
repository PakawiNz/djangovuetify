import io
import json
import zipfile
from collections import defaultdict
from functools import update_wrapper

from django.contrib import admin, messages
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import PermissionDenied
from django.core.management.commands.dumpdata import Command
from django.db.models.base import ModelBase
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone

from utils.model_utils import get_primitive_fields_name, StatefulModel


class CommonAdminSite(AdminSite):
    model_sequences = {}

    def register(self, model_or_iterable, admin_class=None, **options):
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        if admin_class is None and issubclass(model_or_iterable[0], StatefulModel):
            admin_class = StatefulModelAdmin

        if admin_class and admin_class.list_display == '__all__' or options.get('list_display') == '__all__':
            options['list_display'] = get_primitive_fields_name(model_or_iterable[0])

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


# ================================================================================ admin classes

class ReadonlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ButtonActionsAdmin(admin.ModelAdmin):
    change_list_template = 'change_list_actions.html'
    change_form_template = 'change_form_actions.html'
    list_actions = []  # need override
    form_actions = []  # need override

    # ================================================================================ internal definitions
    @property
    def model_info(self):
        return self.model._meta.app_label, self.model._meta.model_name

    @property
    def base_url(self):
        return reverse('admin:%s_%s_changelist' % self.model_info)

    @property
    def list_action_reverse_name(self):
        return '%s_%s_list_action' % self.model_info

    @property
    def form_action_reverse_name(self):
        return '%s_%s_form_action' % self.model_info

    @property
    def list_actions_buttons(self):
        return [dict(action=action, name=action.replace('_', ' ')) for action in self.get_list_actions()]

    @property
    def form_actions_buttons(self):
        return [dict(action=action, name=action.replace('_', ' ')) for action in self.get_form_actions()]

    def action_view(self, request, object_id=None, extra_context=None):
        method = request.method.upper()
        data = request.POST or {}
        action = data.get('action')
        if method != 'POST':
            self.message_user(request, f'Can not do action with {method}', level=messages.ERROR)
            response = None
        elif not object_id and action in self.list_actions:
            response = getattr(self, action)(request)
        elif object_id and action in self.form_actions:
            response = getattr(self, action)(request, object_id)
        else:
            self.message_user(request, f'Action "{action}" is not valid', level=messages.ERROR)
            response = None

        return response or HttpResponseRedirect(self.base_url)

    def get_urls(self):
        urlpatterns = super().get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urlpatterns.insert(0, path(f'action/', wrap(self.action_view), name=self.list_action_reverse_name))
        urlpatterns.insert(0, path(f'<path:object_id>/action/', wrap(self.action_view), name=self.form_action_reverse_name))
        return urlpatterns

    # ================================================================================ overridable definitions
    def get_list_actions(self):
        return self.list_actions

    def get_form_actions(self):
        return self.form_actions


class MasterDataModelAdmin(ButtonActionsAdmin):
    list_actions = ['dump_data']

    @staticmethod
    def download_dump_data(filename, *models):
        timestamp = timezone.now().astimezone().strftime('%Y%m%d-%H%M%S')
        filename = f'{filename}-{timestamp}'

        zip_stream = io.BytesIO()
        zip_archive = zipfile.ZipFile(zip_stream, mode='w', compression=zipfile.ZIP_DEFLATED)

        for model in models:
            app_model = f'{model._meta.app_label}.{model.__name__}'
            dump_stream = io.StringIO()
            command = Command()
            command.stdout = dump_stream
            command.run_from_argv(['manage.py', 'dumpdata', app_model, '--indent=2', '--traceback'])
            zip_archive.writestr(f'{app_model}.json', dump_stream.getvalue())

        zip_archive.close()

        zip_stream.seek(0)
        response = HttpResponse(zip_stream, content_type='text/json')
        response['Content-Disposition'] = f'attachment; filename={filename}.zip'
        return response

    def dump_data(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied()
        return self.download_dump_data(f'dump-{self.model._meta.model_name}', self.model)


class StatefulModelAdmin(ButtonActionsAdmin):
    list_actions = ['diagram']

    def save_model(self, request, obj, form, change):
        obj.internal_save()

    def save_formset(self, request, form, formset, change):
        from utils.model_utils import StatefulModel
        if issubclass(formset.model, StatefulModel):
            formset.save(commit=False)
            for instance in formset.new_objects:
                instance.internal_save()
            for instance, _ in formset.changed_objects:
                instance.internal_save()
            for instance in formset.deleted_objects:
                instance.delete()
            formset.save_m2m()
        else:
            formset.save()

    def get_inlines(self, request, obj):
        class InlineActionLogAdmin(ReadonlyAdminMixin, admin.TabularInline):
            model = self.model.actions.field.model
            fields = get_primitive_fields_name(model)
            readonly_fields = fields
            extra = 0

        return self.inlines + [InlineActionLogAdmin]

    def diagram(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        model = self.model
        nodes = []
        edges = []
        transitions = defaultdict(list)
        node_visited = set()
        nodes.append({
            'id': 'initial',
            'shape': 'circle',
            'fixed': True,
        })
        for state in model.STATUS:
            nodes.append({
                'id': state.value,
                'label': state.text,
                'shape': 'box'
            })
        for status_from_action, status_to in model._get_transition_map().items():
            status_from, action = status_from_action
            edges.append({
                'from': status_from.value if status_from else 'initial',
                'to': status_to.value,
                'arrows': 'to',
                'label': action.name
            })

            status_from_id = status_from.value if status_from else 'initial'
            status_to_id = status_to.value if status_to else 'initial'

            node_visited.add(status_from_id)
            node_visited.add(status_to_id)

            transitions[(status_from_id, status_to_id)].append(action.name)

        nodes = list(filter(lambda x: x['id'] in node_visited, nodes))
        js_nodes = json.dumps(nodes)
        for state in nodes:
            action_list = []
            for to in nodes:
                action_list.append(transitions[(state.get('id'), to.get('id'))])
            state['action_list'] = action_list

        return render(request, 'stateful_model_diagram.html', {
            'model_label': model._meta.label,
            'nodes': js_nodes,
            'edges': json.dumps(edges),
            'states': nodes,
            'transitions': transitions,
        })
