'''
from django.test import TestCase
from django.urls import reverse
from .customuser import CustomUser
import json

class TestAccountSystem(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='TestUser', 
                                              password='password', 
                                              email='test@test.test')
        self.example_data = {
          'login': 'login',
          'password': 'password',
          'email': 'email',
          'rememberMe': True
        }

    def test_registration(self):
        request_data = self.example_data
        
        response = self.client.post(
            reverse('reg'),
            data=json.dumps(request_data),
            content_type='application/json'
        )
'''
# Пока рано система авторизации ещё слишком сыра