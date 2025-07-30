import os
import time
import threading
from flask import Flask, jsonify
import redis
from loguru import logger

# === Конфигурация из переменных окружения (настраиваются через YAML манифест в Kubernetes) ===
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KEY_BATCH_SIZE = int(os.environ.get("KEY_BATCH_SIZE", 20))         # сколько ключей брать за раз из Redis
L2_MIN_KEYS = int(os.environ.get("L2_MIN_KEYS", 5))                # минимальное количество ключей в локальном кэше
BUFFER_KEY_SET = os.environ.get("BUFFER_KEY_SET", "buffer_keys")  # имя множества-буфера в Redis
USED_KEY_ZSET = os.environ.get("USED_KEY_ZSET", "used_keys")      # имя сортированного множества для выданных ключей
FLASK_PORT = int(os.environ.get("FLASK_PORT", 8000))              # порт, на котором работает Flask-сервер

# === Подключение к Redis ===
r = redis.Redis.from_url(REDIS_URL)

# === Инициализация Flask-приложения ===
app = Flask(__name__)

# === L2-кэш (вторичный кэш в памяти) ===
l2_cache = []
l2_lock = threading.Lock()  # блокировка для безопасного доступа из разных потоков

# === Lua-скрипт: атомарно переносит ключи из множества в Redis в отсортированное множество с текущим временем ===
LUA_SCRIPT = """
local keys = redis.call('spop', KEYS[1], ARGV[1])
local now = tonumber(ARGV[2])
for _, key in ipairs(keys) do
    redis.call('zadd', KEYS[2], now, key)
end
return keys
"""

# === Загрузка Lua-скрипта в Redis ===
try:
    LUA_SHA = r.script_load(LUA_SCRIPT)
    logger.info("✅ Lua-скрипт успешно загружен в Redis.")
except redis.RedisError as e:
    logger.error(f"❌ Ошибка загрузки Lua-скрипта в Redis: {e}")
    raise

def fetch_keys_from_redis():
    """Получает пачку ключей из Redis и добавляет их в локальный кэш"""
    try:
        now = int(time.time())
        keys = r.evalsha(LUA_SHA, 2, BUFFER_KEY_SET, USED_KEY_ZSET, KEY_BATCH_SIZE, now)
        keys = [key.decode("utf-8") for key in keys]
        if keys:
            with l2_lock:
                l2_cache.extend(keys)
            logger.info(f"🔁 Получено {len(keys)} ключей из Redis и добавлено в L2-кэш.")
        else:
            logger.warning("⚠️ Redis не вернул ни одного ключа. Возможно, буфер пуст.")
    except redis.RedisError as e:
        logger.error(f"❌ Ошибка при выполнении Lua-скрипта Redis: {e}")

def l2_background_watcher():
    """Фоновый поток: следит за локальным кэшем и пополняет его при необходимости"""
    while True:
        try:
            with l2_lock:
                current_size = len(l2_cache)
            if current_size < L2_MIN_KEYS:
                logger.debug(f"📉 L2-кэш содержит {current_size} ключей, требуется пополнение...")
                fetch_keys_from_redis()
        except Exception as e:
            logger.error(f"💥 Необработанная ошибка в фоновом потоке пополнения: {e}")
        time.sleep(1)

@app.route("/get-key", methods=["GET"])
def get_key():
    """Возвращает один ключ из локального кэша L2"""
    with l2_lock:
        if not l2_cache:
            logger.warning("🚫 Ключей в локальном L2-кэше нет. Возвращаем 503.")
            return jsonify({"error": "Нет доступных ключей"}), 503
        key = l2_cache.pop(0)
    logger.info(f"✅ Ключ успешно выдан клиенту: {key}")
    return jsonify({"key": key})

if __name__ == "__main__":
    logger.info("🚀 Запуск Flask-сервера и фонового потока пополнения L2-кэша...")

    # Старт фонового потока
    threading.Thread(target=l2_background_watcher, daemon=True).start()

    # Запуск Flask-приложения
    app.run(debug=False, host="0.0.0.0", port=FLASK_PORT)
