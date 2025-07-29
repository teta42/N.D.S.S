FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY key_generator.py .

RUN pip install --no-cache-dir psycopg2-binary redis loguru prometheus_client requests

CMD ["python", "key_generator.py"]