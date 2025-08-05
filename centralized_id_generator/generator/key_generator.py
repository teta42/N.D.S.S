import redis
import psycopg2
from loguru import logger
import secrets
from typing import List, Set, Tuple, Dict
import os
import requests
from redis.exceptions import RedisError


def get_current_y_from_redis(redis_client: redis.Redis) -> float:
    """
    Получает значение метрики y из Redis. Если ключ отсутствует, возвращает 0.9.
    """
    try:
        value = redis_client.get('metric:y')
        if value is None:
            logger.warning("Не найдено значение y в Redis, используется значение по умолчанию 0.9")
            return 0.9
        return float(value)
    except (RedisError, ValueError) as e:
        logger.error(f"Ошибка при получении метрики y из Redis: {e}")
        return 0.9

def update_y_in_redis(redis_client: redis.Redis, y_value: float) -> None:
    """
    Обновляет значение метрики y в Redis.
    """
    try:
        redis_client.set('metric:y', y_value)
    except RedisError as e:
        logger.error(f"Ошибка при обновлении метрики y в Redis: {e}")

def get_current_load(prometheus_url: str) -> float:
    """
    Получает текущее значение нагрузки L (RPS) из Prometheus.
    L — количество POST-запросов на endpoint создания заметки.
    """
    query = 'sum(rate(django_http_requests_total_by_view_transport_method_total{view="notes-list", method="POST"}[5m]))'
    try:
        response = requests.get(f"{prometheus_url}api/v1/query", params={'query': query}, timeout=5)
        if response.status_code != 200:
            logger.warning(f"Prometheus вернул код {response.status_code}: {response.text}")
            return 10.0

        result = response.json()
        print(result)
        if result['status'] == 'success' and result['data']['result']:
            return float(result['data']['result'][0]['value'][1])
        else:
            logger.warning("Метрика L не найдена, используется значение по умолчанию 10.0")
            return 10.0
    except Exception as e:
        logger.error(f"Ошибка при получении метрики L: {e}")
        return 10.0

def init_redis() -> redis.Redis:
    """
    Инициализирует клиент Redis.
    """
    try:
        redis_config = {
            'host': os.environ.get('REDIS_HOST', 'my-redis-master.redis.svc.cluster.local'),
            'port': int(os.environ.get('REDIS_PORT', '6379')),
            'db': int(os.environ.get('REDIS_DB', '0')),
            'password': os.environ.get('REDIS_PASSWORD', 'your-strong-password')
        }
        return redis.Redis(**redis_config)
    except Exception as e:
        logger.error(f"Ошибка при инициализации Redis: {e}")
        raise

def init_postgres() -> Dict[str, str]:
    """
    Инициализирует конфигурацию PostgreSQL.
    """
    try:
        return {
            'dbname': os.environ.get('DB_NAME', 'postgres'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASSWORD', 'your-postgres-password'),
            'host': os.environ.get('DB_HOST', 'postgresql-cluster-master.postgres-operator.svc.cluster.local'),
            'port': os.environ.get('DB_PORT', '5432')
        }
    except Exception as e:
        logger.error(f"Ошибка при инициализации PostgreSQL: {e}")
        raise

def calculate_keys_to_generate(L: float, T: int, S: int, y: float) -> Tuple[int, int]:
    """
    Рассчитывает количество ключей G и Y.
    """
    try:
        G = max(0, int(L * T - S))
        if G == 0:
            return 0, 0
        Y = G / y
        return G, int(Y)
    except Exception as e:
        logger.error(f"Ошибка при расчёте G и Y: {e}")
        raise

def generate_keys(Y: int, key_length: int) -> Set[str]:
    """
    Генерирует уникальные ключи.
    """
    try:
        keys = set()
        while len(keys) < Y:
            key = secrets.token_urlsafe(key_length)
            keys.add(key)
        return keys
    except Exception as e:
        logger.error(f"Ошибка при генерации ключей: {e}")
        raise

def check_keys_in_postgres(keys: List[str], db_config: Dict[str, str]) -> List[str]:
    """
    Проверяет, отсутствуют ли ключи в таблицах note и customuser.
    """
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        missing_ids = set(keys)

        # Таблица и соответствующее имя первичного ключа
        tables = {
            'note': 'note_id',
            'customuser': 'user_id',
        }

        for table, pk in tables.items():
            query = f"""
            WITH temp_ids AS (
                SELECT UNNEST(%s::text[]) AS id
            )
            SELECT temp_ids.id
            FROM temp_ids
            LEFT JOIN {table} ON temp_ids.id = {table}.{pk}
            WHERE {table}.{pk} IS NULL;
            """
            cur.execute(query, (keys,))
            missing_ids &= set(row[0] for row in cur.fetchall())

        cur.close()
        conn.close()
        return list(missing_ids)
    except Exception as e:
        logger.error(f"Ошибка при проверке ключей в PostgreSQL: {e}")
        raise

def check_keys_in_redis(keys: List[str], redis_client: redis.Redis) -> List[str]:
    """
    Проверяет, отсутствуют ли ключи в Redis-множестве used_keys.
    """
    try:
        if not keys:
            return []
        results = redis_client.smismember('used_keys', keys)
        missing_keys = [key for key, exists in zip(keys, results) if not exists]
        return missing_keys
    except Exception as e:
        logger.error(f"Ошибка при проверке ключей в Redis: {e}")
        raise

def add_keys_to_buffer(keys: List[str], redis_client: redis.Redis) -> int:
    """
    Добавляет ключи в Redis-множество buffer_keys.
    """
    try:
        if not keys:
            return 0
        added_count = redis_client.sadd('buffer_keys', *keys)
        return added_count
    except Exception as e:
        logger.error(f"Ошибка при добавлении ключей в buffer_keys: {e}")
        raise

def main():
    """
    Основная функция генерации ключей.
    """
    try:
        # Инициализация
        redis_client = init_redis()
        db_config = init_postgres()
        prometheus_url = os.environ.get('PROMETHEUS_URL')
        if not prometheus_url or not prometheus_url.startswith('http'):
            raise ValueError("❌ PROMETHEUS_URL не задан или некорректен (ожидается http://...)")

        T = int(os.environ['TIME_RESERVE'])
        key_length = int(os.environ['KEY_LENGTH'])
        # N = int(os.environ['BUFFER_THRESHOLD'])
        MAX_ATTEMPTS = int(os.environ['MAX_ATTEMPTS'])

        # === Проверка и инициализация множеств в Redis ===
        # buffer_keys — множество
        if not redis_client.exists('buffer_keys'):
            redis_client.sadd('buffer_keys', '__init__')
            redis_client.srem('buffer_keys', '__init__')
            logger.info("🆕 Redis множество 'buffer_keys' было создано.")

        # used_keys — ZSET
        if not redis_client.exists('used_keys'):
            redis_client.zadd('used_keys', {'__init__': 0})
            redis_client.zrem('used_keys', '__init__')
            logger.info("🆕 Redis ZSET 'used_keys' был создан.")

        # Получение текущего количества ключей в Redis-буфере
        current_S = redis_client.scard('buffer_keys')

        # Получение L и y из Prometheus
        L = get_current_load(prometheus_url)
        y = get_current_y_from_redis(redis_client)

        G, Y = calculate_keys_to_generate(L, T, current_S, y)

        # Проверка количества ключей в буфере
        if current_S > G:
            logger.info(f"Ключей в буфере ({current_S}) больше G ({G}), генерация не требуется.")
            return

        attempts = 0
        total_attempted = 0
        total_success = 0

        while attempts < MAX_ATTEMPTS:
            attempts += 1
            if G == 0:
                logger.info("Достаточно ключей в буфере.")
                break

            keys = generate_keys(Y, key_length)
            total_attempted += Y
            missing_in_postgres = check_keys_in_postgres(list(keys), db_config)
            missing_in_redis = check_keys_in_redis(missing_in_postgres, redis_client)
            added_count = add_keys_to_buffer(missing_in_redis, redis_client)
            total_success += added_count

            if total_attempted > 0 and total_success > 0:
                new_y_raw = total_success / total_attempted
                min_y = 0.01
                new_y_clamped = max(new_y_raw, min_y)
                alpha = 0.3  # степень сглаживания

                smoothed_y = alpha * new_y_clamped + (1 - alpha) * y
                update_y_in_redis(redis_client, smoothed_y)

                logger.info(f"Обновлена метрика y: raw={new_y_raw:.4f}, clamped={new_y_clamped:.4f}, smoothed={smoothed_y:.4f}, previous={y:.4f}")
            else:
                logger.info("Недостаточно данных для обновления метрики y (нет успешных ключей).")


            current_S = redis_client.scard('buffer_keys')
            if current_S >= G:
                logger.info(f"Ключей в буфере ({current_S}) >= G ({G}), завершение генерации.")
                break
            else:
                logger.info(f"Ключей в буфере ({current_S}) < G ({G}), повторяем генерацию.")

        if attempts >= MAX_ATTEMPTS:
            logger.warning(f"Достигнуто максимальное количество попыток ({MAX_ATTEMPTS}), генерация остановлена.")

    except Exception as e:
        logger.error(f"Ошибка в основной функции: {e}")


if __name__ == "__main__":
    main()