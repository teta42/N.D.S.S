import redis
import psycopg2
from loguru import logger
import secrets
from typing import List, Set, Tuple, Dict
import os
import requests
from prometheus_client import start_http_server, Gauge

y_gauge = Gauge('unique_yield', 'Доля успешных ключей')

def get_current_y(prometheus_url: str) -> float:
    """
    Получает среднее значение метрики y из Prometheus.
    """
    try:
        query = 'avg_over_time(unique_yield[5m])'
        response = requests.get(f"{prometheus_url}/api/v1/query", params={'query': query})
        result = response.json()
        if result['status'] == 'success' and result['data']['result']:
            return float(result['data']['result'][0]['value'][1])
        else:
            logger.warning("Не удалось получить метрику y, используется значение по умолчанию 0.9")
            return 0.9
    except Exception as e:
        logger.error(f"Ошибка при получении метрики y: {e}")
        return 0.9

def get_current_load(prometheus_url: str) -> float:
    """
    Получает текущее значение нагрузки L из Prometheus.
    L - количество POST запросов на URL создания заметки.
    """
    try:
        # PromQL запрос для получения количества POST запросов на создание заметки
        query = 'sum(rate(django_http_requests_total_by_view_transport_method_total{view="note-list", method="POST"}[5m])) * 300'
        response = requests.get(f"{prometheus_url}/api/v1/query", params={'query': query})
        result = response.json()
        if result['status'] == 'success' and result['data']['result']:
            return float(result['data']['result'][0]['value'][1])
        else:
            logger.warning("Не удалось получить метрику L, используется значение по умолчанию 10.0")
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
            'host': os.environ['REDIS_HOST'],
            'port': os.environ['REDIS_PORT'],
            'db': int(os.environ['REDIS_DB']),
            'password' : os.environ['REDIS_PASSWORD']
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
            'dbname': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD'],
            'host': os.environ['DB_HOST'],
            'port': os.environ['DB_PORT']
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
        for table in ['note', 'customuser']:
            query = f"""
            WITH temp_ids AS (
                SELECT UNNEST(%s::text[]) AS id
            )
            SELECT temp_ids.id
            FROM temp_ids
            LEFT JOIN {table} ON temp_ids.id = {table}.id
            WHERE {table}.id IS NULL;
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
        prometheus_url = os.environ['PROMETHEUS_URL']
        
        T = int(os.environ['TIME_RESERVE'])
        key_length = int(os.environ['KEY_LENGTH'])
        N = int(os.environ['BUFFER_THRESHOLD'])
        MAX_ATTEMPTS = int(os.environ['MAX_ATTEMPTS'])
        
        # Запуск сервера для метрик
        start_http_server(8000)
        
        # Проверка количества ключей в буфере
        current_S = redis_client.scard('buffer_keys')
        if current_S > N:
            logger.info(f"Ключей в буфере ({current_S}) больше N ({N}), генерация не требуется.")
            return
        
        attempts = 0
        total_attempted = 0
        total_success = 0
        
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            # Получение L из Prometheus
            L = get_current_load(prometheus_url)
            y = get_current_y(prometheus_url)
            G, Y = calculate_keys_to_generate(L, T, current_S, y)
            if G == 0:
                logger.info("Достаточно ключей в буфере.")
                break
            
            keys = generate_keys(Y, key_length)
            total_attempted += Y
            missing_in_postgres = check_keys_in_postgres(list(keys), db_config)
            missing_in_redis = check_keys_in_redis(missing_in_postgres, redis_client)
            added_count = add_keys_to_buffer(missing_in_redis, redis_client)
            total_success += added_count
            
            if total_attempted > 0:
                new_y = total_success / total_attempted
                y_gauge.set(new_y)
                logger.info(f"Обновлена метрика y: {new_y}")
            else:
                logger.warning("Не было попыток генерации, метрика y не обновлена.")
            
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