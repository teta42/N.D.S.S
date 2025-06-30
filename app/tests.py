from rest_framework.test import APIClient, APITestCase
from rest_framework.reverse import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Note


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

class NoteTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Создаём пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='password123'
        )

        # Несколько заметок для теста
        self.note_active_mine = Note.objects.create_note(
            user=self.user,
            content="Active mine",
            dead_line=timezone.now() + timedelta(days=1),
            only_authorized=False
        )
        self.note_expired_mine = Note.objects.create_note(
            user=self.user,
            content="Expired mine",
            dead_line=timezone.now() - timedelta(days=1),
            only_authorized=False
        )
        self.note_active_other = Note.objects.create_note(
            user=self.other_user,
            content="Active other",
            dead_line=timezone.now() + timedelta(days=1),
            only_authorized=False
        )
        self.note_only_auth = Note.objects.create_note(
            user=self.other_user,
            content="Only auth",
            dead_line=timezone.now() + timedelta(days=1),
            only_authorized=True
        )
        self.note_expired_only_auth = Note.objects.create_note(
            user=self.other_user,
            content="Expired only auth",
            dead_line=timezone.now() - timedelta(days=1),
            only_authorized=True
        )

    # --- Тесты для list ---

    def test_authenticated_user_gets_only_own_notes(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('notes-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['note_id'], self.note_active_mine.note_id)

    def test_unauthenticated_user_gets_public_notes(self):
        url = reverse('notes-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # note_active_other — public
        self.assertEqual(response.data[0]['note_id'], self.note_active_other.note_id)

    # --- Тесты для retrieve ---

    def test_retrieve_note_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('notes-detail', args=[self.note_active_mine.note_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['note_id'], self.note_active_mine.note_id)

    def test_retrieve_nonexistent_note_returns_404(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('notes-detail', args=['nonexistent'])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_expired_note_returns_404(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('notes-detail', args=[self.note_expired_mine.note_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_only_authorized_note_unauthenticated_returns_403(self):
        url = reverse('notes-detail', args=[self.note_only_auth.note_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_expired_only_authorized_note_returns_404(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('notes-detail', args=[self.note_expired_only_auth.note_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
class CommentTest(APITestCase):
    def setUp(self):
        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        # Логинимся
        self.client.login(username='testuser', password='testpassword')

        # Создаем основную заметку
        self.note = Note.objects.create_note(
            user=self.user,
            content="Основная заметка",
            dead_line="2025-12-31T23:59:59Z",
            only_authorized=False,
            read_only=False
        )

        # Создаем несколько комментариев к этой заметке
        self.comments = [
            Note.objects.create_note(
                user=self.user,
                content=f"Комментарий {i}",
                dead_line="2025-12-31T23:59:59Z",
                only_authorized=False,
                to_comment=self.note
            ) for i in range(3)
        ]

        # URL для получения комментариев
        self.url = reverse('get_comments', args=[self.note.note_id])

    def test_get_comments_returns_paginated_list(self):
        """Проверяет, что список комментариев возвращается с пагинацией"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)  # page_size = 1

    def test_get_comments_count_only(self):
        """Проверяет, что при параметре count-comments=1 возвращается только количество"""
        response = self.client.get(self.url + '?count-comments=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], len(self.comments))

    def test_get_comments_pagination_page_size(self):
        """Проверяет изменение размера страницы через параметр page_size"""
        response = self.client.get(self.url + '?page_size=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_comments_invalid_note_id(self):
        """Проверяет обработку запроса для несуществующей заметки"""
        invalid_url = reverse('get_comments', args=['invalidid'])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)