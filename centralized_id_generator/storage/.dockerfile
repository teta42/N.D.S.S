FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Установка зависимостей
RUN pip install redis loguru

# Создание не-root пользователя
RUN useradd --create-home --shell /bin/bash appuser

# Копирование скрипта
COPY cleanup_used_keys.py /app/cleanup_used_keys.py

# Установка правильного владельца для файлов приложения
RUN chown -R appuser:appuser /app

WORKDIR /app

# Переключение на не-root пользователя
USER appuser

# Команда запуска
CMD ["python", "cleanup_used_keys.py"]
