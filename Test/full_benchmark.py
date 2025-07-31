import time
import random
import string
import logging
import requests
from loguru import logger
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api"
USERNAME = "user_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
PASSWORD = "testpassword123"

session = requests.Session()

def update_csrf():
    r = session.get(f"{BASE_URL}/login/")
    if "csrftoken" in session.cookies:
        session.headers.update({"X-CSRFToken": session.cookies["csrftoken"]})

def register():
    update_csrf()
    logger.info(f"Регистрируем пользователя: {USERNAME}")
    response = session.post(f"{BASE_URL}/register/", data={
        "username": USERNAME,
        "password": PASSWORD,
        "password2": PASSWORD
    })
    response.raise_for_status()
    logger.success("Регистрация прошла успешно")

def login():
    update_csrf()
    logger.info("Логинимся")
    response = session.post(f"{BASE_URL}/login/", data={
        "username": USERNAME,
        "password": PASSWORD
    })
    response.raise_for_status()
    logger.success("Логин успешен")

def create_note(i: int):
    update_csrf()
    data = {
        "title": f"Note {i} - {random.choice(['A', 'B', 'C', 'D'])}",
        "content": ''.join(random.choices(string.ascii_letters + string.digits, k=100)),
        "only_authorized": random.choice([True, False]),
        "burn_after_read": random.choice([True, False]),
        "to_comment": None,
        "is_public": random.choice([True, False])
    }
    logger.debug(f"Создаём заметку {i}")
    response = session.post(f"{BASE_URL}/notes/", json=data)
    if response.status_code != 201:
        logger.error(f"Ошибка создания {i}: {response.status_code} — {response.text}")
    response.raise_for_status()
    return response.json().get("note_id")

def read_note(note_id: str):
    logger.debug(f"Читаем заметку {note_id}")
    r = session.get(f"{BASE_URL}/notes/{note_id}/")
    r.raise_for_status()

def list_notes():
    logger.debug("Список заметок")
    r = session.get(f"{BASE_URL}/notes/")
    r.raise_for_status()

def search_note():
    logger.debug("Поиск заметки")
    r = session.get(f"{BASE_URL}/notes/search/?q=Note")
    if r.status_code not in (200, 400):
        r.raise_for_status()

def random_note():
    logger.debug("Случайная заметка")
    r = session.get(f"{BASE_URL}/notes/random/")
    if r.status_code not in (200, 404):
        r.raise_for_status()

def comments(note_id: str):
    logger.debug("Комментарии к заметке")
    r = session.get(f"{BASE_URL}/notes/{note_id}/comments/")
    if r.status_code not in (200, 404):
        r.raise_for_status()

def logout():
    logger.info("Выход из аккаунта")
    r = session.get(f"{BASE_URL}/logout/")
    r.raise_for_status()

def run_load_test(duration_sec: int):
    start_time = time.time()
    end_time = start_time + duration_sec

    register()
    login()

    note_ids = []
    success = 0
    fail = 0
    total = 0
    i = 0

    while time.time() < end_time:
        try:
            note_id = create_note(i)
            note_ids.append(note_id)

            actions = [
                list_notes,
                search_note,
                random_note,
                lambda: read_note(note_id),
                lambda: comments(note_id),
            ]

            for action in actions:
                try:
                    action()
                    success += 1
                except Exception as e:
                    logger.warning(f"Ошибка при вызове URL: {e}")
                    fail += 1
                total += 1
                time.sleep(0.1)

            i += 1

        except Exception as e:
            logger.error(f"Ошибка при создании заметки {i}: {e}")
            fail += 1
            total += 1
            time.sleep(0.2)

    logout()

    logger.info("Тест завершён")
    logger.info(f"Всего запросов: {total}")
    logger.info(f"Успешных: {success}")
    logger.info(f"Ошибок: {fail}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Нагрузочное тестирование Django API")
    parser.add_argument("--duration", type=int, default=30, help="Длительность теста в секундах")
    args = parser.parse_args()

    run_load_test(args.duration)
