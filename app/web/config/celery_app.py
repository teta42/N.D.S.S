import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Загружаем конфиг из settings.py с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Явно указываем, где искать задачи
app.autodiscover_tasks(['tasks'])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
