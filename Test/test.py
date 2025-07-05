import requests
import threading
import time

# ==== Конфигурация ====
URL = "http://app.localdev.me:5000/time/"  # Замени на нужный URL
REQUESTS_PER_THREAD = 100
NUM_THREADS = 10  # Сколько потоков (параллельных клиентов)
DELAY_BETWEEN_REQUESTS = 1  # Задержка между запросами в секундах (можно оставить 0)

# ==== Функция для потока ====
def send_requests():
    for _ in range(REQUESTS_PER_THREAD):
        try:
            response = requests.get(URL)
            print(f"Status Code: {response.status_code}")
        except Exception as e:
            print(f"Error: {e}")
        
        if DELAY_BETWEEN_REQUESTS > 0:
            time.sleep(DELAY_BETWEEN_REQUESTS)

# ==== Запуск нагрузки ====
if __name__ == "__main__":
    print(f"Starting load test with {NUM_THREADS} threads, {REQUESTS_PER_THREAD} requests each...")
    start_time = time.time()

    threads = []
    for _ in range(NUM_THREADS):
        thread = threading.Thread(target=send_requests)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    end_time = time.time()
    print(f"Load test completed in {end_time - start_time:.2f} seconds")