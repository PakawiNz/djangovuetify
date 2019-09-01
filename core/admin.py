import json
from collections import defaultdict
from functools import update_wrapper

from django import forms
from django.contrib.admin import ModelAdmin
from django.shortcuts import render
from django.urls import path

from core.models import _EnumFormField


class ActionButtonsAdminMixin:
    change_list_template = 'change_list_actions.html'
    change_form_template = 'change_form_actions.html'

    def get_change_list_buttons(self):
        return []

    def get_change_form_buttons(self):
        return []


class StatefulModelAdminForm(forms.ModelForm):
    action = _EnumFormField()

    def __init__(self, data=None, files=None, **kwargs):
        super().__init__(data, files, **kwargs)
        self.fields['action'] = _EnumFormField(
            coerce=int,
            choices=[(e.value, e.name) for e in self.instance.get_allowed_actions()]
        )


class StatefulModelAdmin(ActionButtonsAdminMixin, ModelAdmin):
    form = StatefulModelAdminForm

    def get_readonly_fields(self, request, obj=None):
        return super().get_readonly_fields(request, obj) + ('status',)

    def get_change_list_buttons(self):
        return [
            dict(link='diagram/', name='Diagram'),
        ]

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)

            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urlpatterns = super().get_urls()
        urlpatterns.insert(
            2, path('diagram/', wrap(self.state_diagram_view), name='%s_%s_diagram' % info)
        )
        return urlpatterns

    def save_model(self, request, obj, form, change):
        user = request.user
        action = self.model.ACTION(form.cleaned_data.get('action'))
        obj.transition(user, action)

    def state_diagram_view(self, request):
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
        for status_from, action, status_to in model.TRANSITION:
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
