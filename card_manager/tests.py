from django.test import TestCase
from django.urls import reverse
import json
from .models import Note
from service_accounts.customuser import CustomUser
from datetime import datetime, timedelta, timezone

class TestNote(TestCase):
    def setUp(self): # Подготовка окружения
        self.example_data = {
            "content":"TEST",
            "read_only":"read",
            "dead_line":"2125-01-20T07:12:00.000Z",
            "one_read":"False",
            "only_auth":"False"
        }
        
        # Создаем тестового пользователя
        self.user = CustomUser.objects.create_user(username='anonymous', 
                                                   password='password', 
                                                   email='test@test.test')
        
        self.nowutc = datetime.now(timezone.utc)
  
    def tearDown(self):
        pass
    
    def create_note(self, request_data):
        # Отправка POST-запроса
        response = self.client.post(
            reverse('create_note'),
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Проверка статуса ответа
        sc = response.status_code
        self.assertEqual(sc, 201, f'status_code: {sc}')
        
        # Проверка что записка есть в БД
        node_id = response.json()['note_id']
        
        note_exists = Note.objects.filter(pk=node_id).exists()
        
        self.assertEqual(note_exists, True, 'Записка не создалась')
        
        return node_id
    
    # Проверка на неожиданные коды ответа
    def assert_response_status(self, response, expected_statuses):
        self.assertIn(response, expected_statuses, 
                    f'Неожиданный код статуса: {response}')
    
    def test_deadline_note(self):
        request_data = self.example_data
        days = (1,-1)
        
        for day in days:
            
            request_data['dead_line'] = str((self.nowutc + timedelta(days=day)))
            
            note_id = self.create_note(request_data)
            
            response = self.client.get(
                reverse('read_note', args=[note_id]),
            ).status_code
            
            self.assert_response_status(response, [200,404])
            
            if day > 0:
                self.assertEqual(response, 200, 
                                 'Не могу прочитать живую записку')
            else:
                self.assertEqual(response, 404, 
                                 'Смог прочитать мёртвую записку')
                
    def test_mod_note(self):
        request_data = self.example_data
        mods = ('read', 'write')
        
        for mod in mods:
            request_data['read_only'] = mod
            
            note_id = self.create_note(request_data)
            
            response = self.client.put(
                reverse('write_note', args=[note_id]),
                data=json.dumps({"content":"TEEEEEEST"}),
                content_type='application/json'
            ).status_code
            
            self.assert_response_status(response, [400,200])
            
            if mod == 'read':
                self.assertEqual(response, 400, 
                                 'Получилось изменить записку на чтение')
            elif mod == 'write':
                self.assertEqual(response, 200, 
                                 'Не получилось изменить записку')
     
    def test_one_read(self):
        request_data = self.example_data
        one_read_options = (True, False)
        
        for one_read in one_read_options:
            request_data['one_read'] = one_read
            
            note_id = self.create_note(request_data)
            
            # Первое чтение
            response1 = self.client.get(reverse('read_note', args=[note_id]))
            self.assertEqual(response1.status_code, 200, 
                            'Первое чтение должно быть успешным')
            
            # Второе чтение
            response2 = self.client.get(reverse('read_note', args=[note_id])).status_code
            
            if one_read:
                self.assertEqual(response2, 404, 
                                'Записка должна быть недоступна для повторного чтения')
            else:
                self.assertEqual(response2, 200, 
                                'Записка должна быть доступна для повторного чтения')
                
    def test_auth_note(self):
        request_data = self.example_data
        auth = (True, False)
        
        for i in auth:
            request_data['only_auth'] = i
            
            note_id = self.create_note(request_data)
            
            response = self.client.get(
                reverse('read_note', args=[note_id]),
            ).status_code
            
            self.client.force_login(self.user)
            response_auth = self.client.get(
                reverse('read_note', args=[note_id]),
            ).status_code
            
            self.assert_response_status(response, [404,200])
            self.assert_response_status(response_auth, [404,200])
            
            if i:
                self.assertEqual(response, 404,
                                 'Смог зайти без авторизации')
                self.assertEqual(response_auth, 200,
                                 'Не могу зайти даже авторизованным')
            else:
                self.assertEqual(response, 200,
                                 'Не могу зайти на публичную записку')
                self.assertEqual(response_auth, 200, 
                                 'Не могу зайти на публичную записку даже авторизованным')