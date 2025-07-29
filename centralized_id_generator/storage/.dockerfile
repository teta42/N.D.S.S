FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Установка зависимостей
RUN pip install redis loguru

# Копирование скрипта
COPY cleanup_used_keys.py /app/cleanup_used_keys.py

WORKDIR /app

# Команда запуска
CMD ["python", "cleanup_used_keys.py"]
