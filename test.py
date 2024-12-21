import requests

# Создаем сессию
session = requests.Session()

# Первый запрос для получения cookies и XSRF токена
response = session.get('http://127.0.0.1:8000/create_note/')
print(response.cookies)  # Выводим полученные cookies

# Предположим, что XSRF токен хранится в cookies
xsrf_token = response.cookies.get('XSRF-TOKEN')  # Замените 'XSRF-TOKEN' на имя вашего токена, если оно другое
print(xsrf_token)

# Подготовка данных для POST-запроса
data = {
    'content': 'Я тебя люблю',
    'read_only': 'True',
    'X-XSRF-TOKEN': xsrf_token  # Добавляем XSRF токен в данные
}

# Отправляем POST-запрос с cookies и XSRF токеном
response = session.post('http://127.0.0.1:8000/create_note/', data=data)