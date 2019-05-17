from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseNotFound
from django.shortcuts import render
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


def not_found(request):
    return HttpResponseNotFound()


def vue(request):
    return render(request, 'index.html')


class AuthenticationView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({
            'authenticated': request.user.is_authenticated,
            'username': request.user.username,
        })

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return self.get(request)

        raise ValidationError({'message': 'Invalid credential.'})

    def delete(self, request):
        logout(request)
        return self.get(request)
