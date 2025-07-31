import os
import time
import threading
from flask import Flask, jsonify
import redis
from loguru import logger
import queue
import requests

# === Конфигурация из переменных окружения (настраиваются через YAML манифест в Kubernetes) ===
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
KEY_BATCH_SIZE = int(os.environ.get("KEY_BATCH_SIZE", 20))         # сколько ключей брать за раз из Redis
BUFFER_KEY_SET = os.environ.get("BUFFER_KEY_SET", "buffer_keys")  # имя множества-буфера в Redis
USED_KEY_ZSET = os.environ.get("USED_KEY_ZSET", "used_keys")      # имя сортированного множества для выданных ключей
FLASK_PORT = int(os.environ.get("FLASK_PORT", 8000))              # порт, на котором работает Flask-сервер
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL")                  # URL Prometheus (например http://prometheus:9090)

# === Подключение к Redis ===
r = redis.Redis.from_url(REDIS_URL)

# === Инициализация Flask-приложения ===
app = Flask(__name__)

# === L2-кэш (вторичный кэш в памяти) ===
l2_cache = queue.Queue()

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


def get_current_load_for_pod(prometheus_url: str) -> float:
    """
    Получает нагрузку (L) для конкретного инстанса Django из Prometheus,
    используя имя пода из переменной окружения POD_NAME.
    """
    pod_name = os.environ.get("POD_NAME")
    if not pod_name:
        logger.error("POD_NAME не задан в окружении")
        return 0.0

    query = (
        f'sum(rate(django_http_requests_total_by_view_transport_method_total{{'
        f'view="note-list", method="POST", pod="{pod_name}"}}[5m])) * 300'
    )

    try:
        response = requests.get(f"{prometheus_url}/api/v1/query", params={'query': query}, timeout=5)
        result = response.json()

        if result['status'] == 'success' and result['data']['result']:
            value = float(result['data']['result'][0]['value'][1])
            logger.debug(f"Нагрузка для пода {pod_name}: {value}")
            return value
        else:
            logger.warning(f"Метрика не найдена для пода {pod_name}, возвращаем 0.0")
            return 0.0

    except Exception as e:
        logger.error(f"Ошибка при получении нагрузки из Prometheus: {e}")
        return 0.0


def load_to_min_keys(load: float) -> int:
    """
    Преобразует нагрузку на инстанс в минимальное количество ключей для L2_MIN_KEYS.
    Здесь можно задать свою логику масштабирования.

    Например:
    - Минимум 10 ключей при нагрузке <= 10
    - При нагрузке выше 10, линейно увеличиваем количество ключей
    """
    base_min = 10
    if load <= 10:
        return base_min
    else:
        # например, для каждого +10 запросов добавляем 10 ключей
        extra_keys = int((load - 10) / 10) * 10
        return base_min + extra_keys


def fetch_keys_from_redis():
    try:
        now = int(time.time())
        keys = r.evalsha(LUA_SHA, 2, BUFFER_KEY_SET, USED_KEY_ZSET, KEY_BATCH_SIZE, now)
        keys = [key.decode("utf-8") for key in keys]
        if keys:
            for key in keys:
                l2_cache.put(key)  # потокобезопасно кладём ключи в очередь
            logger.info(f"🔁 Получено {len(keys)} ключей из Redis и добавлено в L2-кэш.")
        else:
            logger.warning("⚠️ Redis не вернул ни одного ключа. Возможно, буфер пуст.")
    except redis.RedisError as e:
        logger.error(f"❌ Ошибка при выполнении Lua-скрипта Redis: {e}")


def l2_background_watcher():
    while True:
        try:
            current_size = l2_cache.qsize()
            load = get_current_load_for_pod(PROMETHEUS_URL) if PROMETHEUS_URL else 0.0
            min_keys = load_to_min_keys(load)

            if current_size < min_keys:
                logger.debug(f"📉 L2-кэш содержит {current_size} ключей, требуется пополнение (минимум {min_keys})...")
                fetch_keys_from_redis()
        except Exception as e:
            logger.error(f"💥 Необработанная ошибка в фоновом потоке пополнения: {e}")
        time.sleep(1)


@app.route("/get-key", methods=["GET"])
def get_key():
    try:
        key = l2_cache.get_nowait()  # пытаемся получить ключ, если пусто — исключение
        logger.info(f"✅ Ключ успешно выдан клиенту: {key}")
        return jsonify({"key": key})
    except queue.Empty:
        logger.warning("🚫 Ключей в локальном L2-кэше нет. Возвращаем 503.")
        return jsonify({"error": "Нет доступных ключей"}), 503


if __name__ == "__main__":
    logger.info("🚀 Запуск Flask-сервера и фонового потока пополнения L2-кэша...")

    threading.Thread(target=l2_background_watcher, daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=FLASK_PORT)
