import redis
import time
import os
from loguru import logger

# Параметры подключения из переменных окружения
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
USED_KEYS_SET = os.getenv("USED_KEYS_SET", "used_keys")
EXPIRE_MINUTES = int(os.getenv("EXPIRE_MINUTES", 15))

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/cleanup.log")

logger.remove()
logger.add(LOG_FILE, rotation="1 MB", retention="7 days", level=LOG_LEVEL)
logger.add(lambda msg: print(msg, end=""), level=LOG_LEVEL)

def main():
    """
    Подключается к Redis и удаляет устаревшие ключи из сортированного множества.
    
    Ключи считаются устаревшими, если их score (временная метка UNIX) меньше чем N минут назад.
    
    Используемые переменные окружения:
    - REDIS_HOST: хост Redis (по умолчанию 'localhost')
    - REDIS_PORT: порт Redis (по умолчанию 6379)
    - REDIS_DB: номер базы (по умолчанию 0)
    - REDIS_PASSWORD: пароль (по умолчанию None)
    - USED_KEYS_SET: имя множества (по умолчанию 'used_keys')
    - EXPIRE_MINUTES: порог устаревания в минутах (по умолчанию 15)
    - LOG_FILE: путь к лог-файлу (по умолчанию '/var/log/cleanup.log')
    - LOG_LEVEL: уровень логирования (по умолчанию 'INFO')
    """
    logger.info("🚀 Starting cleanup script")

    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            socket_timeout=5
        )
        logger.info(f"🔗 Connected to Redis at {REDIS_HOST}:{REDIS_PORT}, DB {REDIS_DB}")
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
