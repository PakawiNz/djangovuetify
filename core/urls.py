from django.urls import path

from . import views

urlpatterns = [
    path('auth/', views.AuthenticationView.as_view()),
]