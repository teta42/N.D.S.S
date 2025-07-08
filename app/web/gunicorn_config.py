import multiprocessing

# Биндим на все интерфейсы на порту 8000
bind = "0.0.0.0:8000"

# Количество воркеров = количество ядер * 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Тип воркера — стандартный синхронный
worker_class = "sync"

# Таймаут запроса
timeout = 30
graceful_timeout = 30

# Автоперезапуск при утечках
max_requests = 1000
max_requests_jitter = 50

# Логирование
loglevel = "info"
accesslog = "-"        # Логи доступа в stdout
errorlog = "-"         # Логи ошибок в stdout

# Вывод логов Django в консоль
capture_output = True

# Прелоад кода приложения (экономит память через copy-on-write)
preload_app = True

# Название приложения (не обязательно)
proc_name = "drf-app"

# Опционально: путь до pid-файла
# pidfile = "/tmp/gunicorn.pid"
