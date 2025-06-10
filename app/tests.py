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
        
        response = self.client.put(reverse('update_account'), updated_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"username": updated_data['username']})
        
        updated_user = User.objects.get(pk=self.default_user.pk)
        self.assertEqual(updated_user.username, updated_data['username'])
        self.assertTrue(updated_user.check_password(updated_data['password']))
    
    def test_update_account_only_username(self):
        """Проверяет обновление только имени пользователя через PATCH."""
        new_username = 'new_username'
        self.client.force_login(self.default_user)

        response = self.client.patch(reverse('update_account'), {'username': new_username}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], new_username)

        updated_user = User.objects.get(pk=self.default_user.pk)
        self.assertEqual(updated_user.username, new_username)
        self.assertTrue(updated_user.check_password(self.default_user_data['password']))


    def test_update_account_only_password(self):
        """Проверяет обновление только пароля через PATCH."""
        new_password = 'new_secure_pass'
        self.client.force_login(self.default_user)

        response = self.client.patch(reverse('update_account'), {'password': new_password}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.default_user_data['username'])

        updated_user = User.objects.get(pk=self.default_user.pk)
        self.assertEqual(updated_user.username, self.default_user_data['username'])
        self.assertTrue(updated_user.check_password(new_password))


    def test_update_account_both_fields(self):
        """Проверяет полное обновление имени и пароля через PUT."""
        updated_data = {'username': 'new_name', 'password': 'new_pass'}
        self.client.force_login(self.default_user)

        response = self.client.put(reverse('update_account'), updated_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], updated_data['username'])

        updated_user = User.objects.get(pk=self.default_user.pk)
        self.assertEqual(updated_user.username, updated_data['username'])
        self.assertTrue(updated_user.check_password(updated_data['password']))


    def test_update_account_same_username(self):
        """Проверяет, что можно отправить тот же username без ошибки."""
        same_data = {'username': self.default_user_data['username']}
        self.client.force_login(self.default_user)

        response = self.client.patch(reverse('update_account'), same_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.default_user_data['username'])


    def test_update_account_username_already_taken(self):
        """Проверяет, что нельзя установить существующее имя пользователя."""
        another_user = User.objects.create_user(username='another_user', password='pass123')
        self.client.force_login(self.default_user)

        response = self.client.patch(reverse('update_account'), {'username': another_user.username}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
        self.assertEqual(
            str(response.data['username'][0]),
            'Это имя пользователя уже занято.'
        )
    
    def test_update_account_with_partial_data(self):
        """Проверяет обновление части данных пользователя через PATCH-запрос."""
        partial_data = {'username': 'partially_updated'}
        self.client.force_login(self.default_user)
        
        response = self.client.patch(reverse('update_account'), partial_data, format='json')
        
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