import redis
import time
import os
from loguru import logger

# Параметры подключения из переменных окружения
REDIS_URL = os.getenv("REDIS_URL", 'redis://:your-strong-password@my-redis-master.redis.svc.cluster.local:6379/0')
USED_KEYS_SET = os.getenv("USED_KEYS_SET", "used_keys")

# Обработка EXPIRE_MINUTES с обработкой ошибок
try:
    EXPIRE_MINUTES = int(os.getenv("EXPIRE_MINUTES", 15))
except ValueError:
    logger.warning("EXPIRE_MINUTES не является числом, используется значение по умолчанию 15")
    EXPIRE_MINUTES = 15

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/cleanup.log")

logger.remove()
# Попытка добавить файловый логгер, если директория доступна
try:
    logger.add(LOG_FILE, rotation="1 MB", retention="7 days", level=LOG_LEVEL)
except Exception as e:
    logger.warning(f"Не удалось настроить файловый логгер: {e}. Логи будут только в stdout.")

logger.add(lambda msg: print(msg, end=""), level=LOG_LEVEL)

def main():
    """
    Подключается к Redis и удаляет устаревшие ключи из сортированного множества.
    
    Ключи считаются устаревшими, если их score (временная метка UNIX) меньше чем N минут назад.
    
    Используемые переменные окружения:
    - REDIS_URL - REDIS_URL
    - USED_KEYS_SET: имя множества (по умолчанию 'used_keys')
    - EXPIRE_MINUTES: порог устаревания в минутах (по умолчанию 15)
    - LOG_FILE: путь к лог-файлу (по умолчанию '/var/log/cleanup.log')
    - LOG_LEVEL: уровень логирования (по умолчанию 'INFO')
    """
    logger.info("🚀 Starting cleanup script")
    
    # Проверка наличия REDIS_URL
    if not REDIS_URL:
        logger.error("REDIS_URL не задан. Выход.")
        return
    
    # Log all environment variables for debugging
    logger.debug("All environment variables:")
    for key, value in os.environ.items():
        logger.debug(f"  {key}: {value}")

    try:
        r = redis.from_url(REDIS_URL)
        logger.info(f"🔗 Connected to Redis")
    except redis.RedisError as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return

    current_time = time.time()
    threshold = current_time - EXPIRE_MINUTES * 60

    try:
        removed = r.zremrangebyscore(USED_KEYS_SET, 0, threshold)
        logger.success(f"🧹 Removed {removed} expired keys from '{USED_KEYS_SET}' (older than {EXPIRE_MINUTES} min)")
    except redis.RedisError as e:
        logger.error(f"❌ Failed to remove expired keys: {e}")

if __name__ == "__main__":
    main()
