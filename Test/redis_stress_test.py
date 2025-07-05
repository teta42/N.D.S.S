import time
import redis
from threading import Thread
from prettytable import PrettyTable
from datetime import datetime

# Глобальные конфигурации (вместо аргументов командной строки)
GLOBAL_CONFIG = {
    "REDIS_MASTER": {
        "host": "localhost",
        "port": 6379,
        "password": "your-strong-password",
        "db": 0
    },
    "REDIS_REPLICA": {
        "host": "localhost",
        "port": 8379,
        "password": "your-strong-password",
        "db": 0
    },
    "TEST_DURATION": 60,  # Длительность теста в секундах
    "WRITE_THREADS": 5,   # Количество потоков для записи
    "READ_THREADS": 10,   # Количество потоков для чтения
    "KEY_PREFIX": "stress_test",
    "DATA_SIZE": 1024     # Размер данных в байтах
}

# Глобальные результаты
GLOBAL_RESULTS = {
    "start_time": None,
    "end_time": None,
    "master_write_ops": 0,
    "replica_read_ops": 0,
    "errors": 0,
    "latencies": []
}

def print_banner():
    """Выводит красивый баннер с информацией о тесте"""
    print("\n" + "=" * 80)
    print("Redis Stress Test".center(80))
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(80))
    print("=" * 80)
    print(f"\nConfiguration:")
    config_table = PrettyTable(["Parameter", "Value"])
    config_table.align["Parameter"] = "l"
    config_table.align["Value"] = "l"
    for key, value in GLOBAL_CONFIG.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                config_table.add_row([f"{key}.{subkey}", subvalue])
        else:
            config_table.add_row([key, value])
    print(config_table)
    print("\nStarting test...\n")

def generate_data(size):
    """Генерирует тестовые данные заданного размера"""
    return "x" * size

def write_worker(worker_id):
    """Поток для записи данных в Redis master"""
    r = redis.StrictRedis(**GLOBAL_CONFIG["REDIS_MASTER"])
    data = generate_data(GLOBAL_CONFIG["DATA_SIZE"])
    
    while time.time() < GLOBAL_RESULTS["end_time"]:
        try:
            key = f"{GLOBAL_CONFIG['KEY_PREFIX']}:{worker_id}:{time.time()}"
            r.set(key, data)
            GLOBAL_RESULTS["master_write_ops"] += 1
        except Exception as e:
            GLOBAL_RESULTS["errors"] += 1
            print(f"Write error in worker {worker_id}: {str(e)}")

def read_worker(worker_id):
    """Поток для чтения данных из Redis replica"""
    r = redis.StrictRedis(**GLOBAL_CONFIG["REDIS_REPLICA"])
    
    while time.time() < GLOBAL_RESULTS["end_time"]:
        try:
            # Читаем случайный ключ (может не существовать - это нормально)
            key = f"{GLOBAL_CONFIG['KEY_PREFIX']}:*"
            keys = r.keys(key)
            if keys:
                r.get(keys[0])
                GLOBAL_RESULTS["replica_read_ops"] += 1
        except Exception as e:
            GLOBAL_RESULTS["errors"] += 1
            print(f"Read error in worker {worker_id}: {str(e)}")

def run_stress_test():
    """Запускает стресс-тест"""
    GLOBAL_RESULTS["start_time"] = time.time()
    GLOBAL_RESULTS["end_time"] = GLOBAL_RESULTS["start_time"] + GLOBAL_CONFIG["TEST_DURATION"]
    
    # Создаем и запускаем потоки
    threads = []
    
    # Потоки записи
    for i in range(GLOBAL_CONFIG["WRITE_THREADS"]):
        t = Thread(target=write_worker, args=(i,))
        t.start()
        threads.append(t)
    
    # Потоки чтения
    for i in range(GLOBAL_CONFIG["READ_THREADS"]):
        t = Thread(target=read_worker, args=(i,))
        t.start()
        threads.append(t)
    
    # Мониторинг прогресса
    while time.time() < GLOBAL_RESULTS["end_time"]:
        elapsed = time.time() - GLOBAL_RESULTS["start_time"]
        remaining = GLOBAL_RESULTS["end_time"] - time.time()
        print(f"Progress: {elapsed:.1f}s / {GLOBAL_CONFIG['TEST_DURATION']}s | "
              f"Write OPS: {GLOBAL_RESULTS['master_write_ops']} | "
              f"Read OPS: {GLOBAL_RESULTS['replica_read_ops']} | "
              f"Errors: {GLOBAL_RESULTS['errors']} | "
              f"Remaining: {remaining:.1f}s", end="\r")
        time.sleep(1)
    
    # Ожидаем завершения всех потоков
    for t in threads:
        t.join()
    
    print("\n\nTest completed!")

def print_results():
    """Выводит красивые результаты теста"""
    duration = GLOBAL_RESULTS["end_time"] - GLOBAL_RESULTS["start_time"]
    write_ops_sec = GLOBAL_RESULTS["master_write_ops"] / duration
    read_ops_sec = GLOBAL_RESULTS["replica_read_ops"] / duration
    
    print("\n" + "=" * 80)
    print("Test Results".center(80))
    print("=" * 80)
    
    results_table = PrettyTable(["Metric", "Value"])
    results_table.align["Metric"] = "l"
    results_table.align["Value"] = "l"
    
    results_table.add_row(["Test Duration", f"{duration:.2f} seconds"])
    results_table.add_row(["Total Write Operations", GLOBAL_RESULTS["master_write_ops"]])
    results_table.add_row(["Write Operations/sec", f"{write_ops_sec:.2f}"])
    results_table.add_row(["Total Read Operations", GLOBAL_RESULTS["replica_read_ops"]])
    results_table.add_row(["Read Operations/sec", f"{read_ops_sec:.2f}"])
    results_table.add_row(["Total Errors", GLOBAL_RESULTS["errors"]])
    
    print(results_table)
    print("=" * 80 + "\n")

def main():
    print_banner()
    run_stress_test()
    print_results()

if __name__ == "__main__":
    main()
