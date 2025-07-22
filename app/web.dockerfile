FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN adduser --uid 5678 --disabled-password --gecos "" appuser

WORKDIR /app

# Сначала копируем зависимости отдельно — для кэша
COPY web/requirements.txt ./

RUN pip install --upgrade pip \
 && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Копируем весь проект после установки зависимостей
COPY web/ .

# Смена владельца
RUN chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# collectstatic + подготовка директорий
RUN mkdir -p /app/staticfiles \
 && python manage.py collectstatic --noinput

# По умолчанию запускаем gunicorn, но можешь переопределить через docker-compose
CMD ["gunicorn", "-c", "gunicorn_config.py", "config.wsgi:application"]
