from rest_framework.test import APIClient, APITestCase
from rest_framework.reverse import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountTest(APITestCase):
    """Тесты для проверки функциональности аккаунта пользователя."""
    
    def setUp(self):
        """Инициализация тестового клиента и создание тестового пользователя."""
        self.client = APIClient()
        self.default_user_data = {'username': 'default_user', 'password': 'default_pass'}
        self.default_user = User.objects.create_user(**self.default_user_data)
    
    def test_reg_creates_new_user(self):
        """Проверяет успешную регистрацию нового пользователя."""
        new_user_data = {'username': 'new_user', 'password': 'new_pass'}
        
        response = self.client.post(reverse('reg'), new_user_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username=new_user_data['username']).exists())
    
    def test_reg_rejects_duplicate_username(self):
        """Проверяет, что регистрация отклоняет дублирующийся username."""
        duplicate_data = {'username': 'default_user', 'password': 'another_pass'}
        
        response = self.client.post(reverse('reg'), duplicate_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_login_returns_session_cookie(self):
        """Проверяет успешный вход пользователя и наличие сессионной куки."""
        response = self.client.post(reverse('login'), self.default_user_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('sessionid' in response.cookies)
    
    def test_logout_clears_authentication(self):
        """Проверяет, что logout завершает сессию пользователя."""
        self.client.force_login(self.default_user)
        self.client.get(reverse('logout'))
        
        response = self.client.get(reverse('update_account'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_account_modifies_user_data(self):
        """Проверяет обновление данных пользователя через PUT-запрос."""
        updated_data = {'username': 'updated_user', 'password': 'updated_pass'}
        self.client.force_login(self.default_user)
        
        response = self.client.put(reverse('update_account'), updated_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"username": updated_data['username']})
        
        updated_user = User.objects.get(pk=self.default_user.pk)
        self.assertEqual(updated_user.username, updated_data['username'])
        self.assertTrue(updated_user.check_password(updated_data['password']))
    
    def test_update_account_with_partial_data(self):
        """Проверяет обновление части данных пользователя через PATCH-запрос."""
        partial_data = {'username': 'partially_updated'}
        self.client.force_login(self.default_user)
        
        response = self.client.patch(reverse('update_account'), partial_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['username'], partial_data['username'])
    
    def test_delete_account_removes_user(self):
        """Проверяет удаление аккаунта пользователя."""
        user_to_delete = User.objects.create_user(
            username='delete_me', password='delete_pass'
        )
        self.client.force_login(user_to_delete)
        
        response = self.client.delete(reverse('delete_account'))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(username='delete_me').exists())