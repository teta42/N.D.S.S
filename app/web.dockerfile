FROM python:3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY web/ /app/

# Установка зависимостей
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

RUN pip install meilisearch==0.36.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/

# Создаем пользователя
RUN adduser --uid 5678 --disabled-password --gecos "" appuser && \
    chown -R appuser /app

USER appuser

# Собираем статику уже от имени appuser, чтобы не было проблем с правами
RUN python manage.py collectstatic --noinput

# Создаем директорию под статику
RUN mkdir -p /app/staticfiles

CMD ["gunicorn", "-c", "gunicorn_config.py", "config.wsgi:application"]
