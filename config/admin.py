from django.contrib.admin.apps import AdminConfig


class CommonAdminConfig(AdminConfig):
    default_site = 'utils.admin_utils.CommonAdminSite'