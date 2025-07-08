FROM python:3-slim

# Отключаем создание .pyc файлов
ENV PYTHONDONTWRITEBYTECODE=1

# Отключаем буферизацию вывода (для логов)
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем содержимое папки web (убедись, что в ней есть requirements.txt и код)
COPY web/ /app/

# Устанавливаем зависимости
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

RUN python manage.py collectstatic --noinput

RUN mkdir /app/staticfiles

# Создаем пользователя без пароля
RUN adduser --uid 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app

# Переключаемся на этого пользователя
USER appuser

# Команда запуска приложения (важно: gunicorn требует exec-формат и правильные кавычки)
CMD ["gunicorn", "-c", "gunicorn_config.py", "config.wsgi:application"]
