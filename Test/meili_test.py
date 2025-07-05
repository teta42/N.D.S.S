import random
import string
import time
from datetime import datetime
from meilisearch import Client
from rich.console import Console
from rich.table import Table
from rich.progress import track

# ==================== Настройки ====================
MEILISEARCH_URL = "http://localhost:7700"
API_KEY = ""  # Укажите, если включена аутентификация
INDEX_UID = "benchmark_index"
DOCUMENT_COUNT = 10_000
SEARCH_COUNT = 1_000
MAX_WORD_LENGTH = 6
console = Console()

# ==================== Вспомогательные функции ====================

def random_word(length=5):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def generate_document(i):
    return {
        "id": i,
        "title": f"Document {i} title",
        "content": " ".join([random_word(random.randint(2, MAX_WORD_LENGTH)) for _ in range(20)]),
        "timestamp": datetime.now().isoformat()
    }

# ==================== Основная логика ====================

def main():
    console.rule("[bold blue]Начало тестирования Meilisearch")

    client = Client(MEILISEARCH_URL)

    # 1. Удаление существующего индекса (если есть)
    try:
        client.get_index(INDEX_UID).delete()
        console.print(f"[yellow]Старый индекс '{INDEX_UID}' удалён.")
    except Exception as e:
        console.print(f"[green]Индекс '{INDEX_UID}' не существует — создаём новый.")

    # 2. Создание индекса
    console.print(f"[blue]Создаём индекс '{INDEX_UID}'...")
    task_info = client.create_index(uid=INDEX_UID)  # Получаем TaskInfo

    # Ждём завершения задачи создания индекса
    while True:
        task = client.get_task(task_info.task_uid)
        if task.status == "succeeded" or task.status == "failed":
            break
        time.sleep(0.5)

    if task.status == "failed":
        console.print(f"[red]Ошибка при создании индекса: {task.error}")
        return

    index = client.get_index(INDEX_UID)  # Получаем готовый индекс
    console.print(f"[green]Индекс '{INDEX_UID}' создан")

    # 3. Генерация документов
    console.print(f"[blue]Генерируем {DOCUMENT_COUNT} документов...")
    documents = [generate_document(i) for i in track(range(DOCUMENT_COUNT), description="Генерация данных")]

    # 4. Добавление документов
    console.print(f"[blue]Загружаем {len(documents)} документов в Meilisearch...")

    task_info = index.add_documents(documents)

    # Ждём завершения задачи
    while True:
        task = client.get_task(task_info.task_uid)
        if task.status == "succeeded" or task.status == "failed":
            break
        time.sleep(0.5)

    if task.status == "failed":
        console.print(f"[red]Ошибка при загрузке документов: {task.error}")
        return

    console.print(f"[green]Документы успешно загружены (ID задачи: {task_info.task_uid})")

    # 5. Подготовка к поисковым запросам
    console.print(f"[blue]Выполняем {SEARCH_COUNT} поисковых запросов...")

    search_times = []
    for _ in track(range(SEARCH_COUNT), description="Выполнение поисков"):
        word = random_word(random.randint(2, MAX_WORD_LENGTH))
        start = time.time()
        try:
            results = index.search(word, {"limit": 10})
            duration = time.time() - start
            search_times.append(duration)
        except Exception as e:
            console.print(f"[red]Ошибка при поиске: {e}")

    # 6. Статистика
    avg_time = sum(search_times) / len(search_times)
    p95 = sorted(search_times)[int(len(search_times)*0.95)]

    table = Table(title="📊 Результаты тестирования")
    table.add_column("Метрика", style="cyan")
    table.add_column("Значение", style="magenta")

    table.add_row("Всего документов", str(DOCUMENT_COUNT))
    table.add_row("Всего поисков", str(SEARCH_COUNT))
    table.add_row("Среднее время поиска", f"{avg_time:.4f} сек")
    table.add_row("P95 время поиска", f"{p95:.4f} сек")

    console.print(table)
    console.rule("[bold green]Тестирование завершено")

if __name__ == "__main__":
    main()