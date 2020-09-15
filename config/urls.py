from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path

from core.views import not_found, vue

api_urlpatterns = [
    path('core/', include('core.urls')),
    *[path(f'{app}/', include(f'apps.{app}.urls')) for app in settings.USER_APPS],
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((api_urlpatterns, 'api'))),
    re_path('(?:admin|api|static|media)/.*', not_found),
    re_path('.*', vue),
]
