import psycopg2
import threading
import time
from random import randint, choice
from string import ascii_letters
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os

console = Console()

# Конфигурация подключения к БД
# Password should be set via environment variable
MASTER_CONFIG = {
  "dbname": "postgres",
  "user": "postgres",
  "password": os.environ.get("TEST_POSTGRES_PASSWORD", "qtKOJ9Ah9AzP8VVo8hhm4NTZ8Jd9MPBcehicosVl1QjXZE0GJO1k1YweLAbMZ4Hx"),
  "host": "127.0.0.1",  # мастер
  "port": "5432"
}

REPLICA_CONFIG = {
    **MASTER_CONFIG,
    "port": "6432"  # реплика
}

TABLE_NAME = "stress_test_table"

# Глобальные переменные для статистики
stats = {
    "master": {
        "inserts": 0,
        "selects": 0,
        "updates": 0,
        "deletes": 0,
        "complex_queries": 0,
        "errors": 0,
    },
    "replica": {
        "selects": 0,
        "errors": 0,
    },
    "lock": threading.Lock()
}

TEST_DURATION = 30  # секунд
NUM_THREADS_MASTER = 3
NUM_THREADS_REPLICA = 2

def random_string(length=10):
    return ''.join(choice(ascii_letters) for _ in range(length))

def setup_table():
    """Создание тестовой таблицы"""
    try:
        conn = psycopg2.connect(**MASTER_CONFIG)
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                name TEXT,
                value INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        console.print(f"[red]Ошибка при создании таблицы:[/red] {e}")

def complex_query(conn):
    """Выполняет сложный SQL-запрос с CTE и оконной функцией"""
    try:
        cur = conn.cursor()
        cur.execute(f"""
            WITH ranked_data AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY value DESC) AS rank
                FROM {TABLE_NAME}
            )
            SELECT name, value, rank
            FROM ranked_data
            WHERE rank <= 5;
        """)
        cur.fetchall()
        with stats["lock"]:
            stats["master"]["complex_queries"] += 1
    except Exception as e:
        with stats["lock"]:
            stats["master"]["errors"] += 1
        console.print(f"[red]Ошибка выполнения сложного запроса:[/red] {e}")

def stress_master_operation():
    """Функция для выполнения CRUD-операций на мастере"""
    try:
        conn = psycopg2.connect(**MASTER_CONFIG)
        while not stop_flag.is_set():
            op = choice(["insert", "select", "update", "delete", "complex"])

            if op == "insert":
                name = random_string()
                value = randint(1, 100)
                cur = conn.cursor()
                cur.execute(f"INSERT INTO {TABLE_NAME} (name, value) VALUES (%s, %s)", (name, value))
                conn.commit()
                cur.close()
                with stats["lock"]:
                    stats["master"]["inserts"] += 1

            elif op == "select":
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY RANDOM() LIMIT 1")
                cur.fetchone()
                conn.commit()
                cur.close()
                with stats["lock"]:
                    stats["master"]["selects"] += 1

            elif op == "update":
                cur = conn.cursor()
                cur.execute(f"SELECT id FROM {TABLE_NAME} ORDER BY RANDOM() LIMIT 1")
                result = cur.fetchone()
                if result:
                    new_value = randint(1, 100)
                    cur.execute(f"UPDATE {TABLE_NAME} SET value = %s WHERE id = %s", (new_value, result[0]))
                    conn.commit()
                cur.close()
                with stats["lock"]:
                    stats["master"]["updates"] += 1

            elif op == "delete":
                cur = conn.cursor()
                cur.execute(f"SELECT id FROM {TABLE_NAME} ORDER BY RANDOM() LIMIT 1")
                result = cur.fetchone()
                if result:
                    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE id = %s", (result[0],))
                    conn.commit()
                cur.close()
                with stats["lock"]:
                    stats["master"]["deletes"] += 1

            elif op == "complex":
                complex_query(conn)

        conn.close()
    except Exception as e:
        with stats["lock"]:
            stats["master"]["errors"] += 1
        console.print(f"[red]Ошибка в потоке мастера {threading.get_ident()}:[/red] {e}")

def stress_replica_operation():
    """Функция для выполнения SELECT на реплике"""
    try:
        conn = psycopg2.connect(**REPLICA_CONFIG)
        while not stop_flag.is_set():
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            cur.fetchone()
            cur.close()
            with stats["lock"]:
                stats["replica"]["selects"] += 1
            time.sleep(0.1)
        conn.close()
    except Exception as e:
        with stats["lock"]:
            stats["replica"]["errors"] += 1
        console.print(f"[red]Ошибка в потоке реплики {threading.get_ident()}:[/red] {e}")

stop_flag = threading.Event()

def run_stress_test():
    console.print(Panel.fit("🚀 [bold green]Старт стресс-теста PostgreSQL[/bold green] 🚀"))
    setup_table()

    master_threads = []
    replica_threads = []

    for i in range(NUM_THREADS_MASTER):
        thread = threading.Thread(target=stress_master_operation)
        master_threads.append(thread)
        thread.start()

    for i in range(NUM_THREADS_REPLICA):
        thread = threading.Thread(target=stress_replica_operation)
        replica_threads.append(thread)
        thread.start()

    start_time = time.time()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:.0f}%"),
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Тестирование...", total=TEST_DURATION)
        while time.time() - start_time < TEST_DURATION and not stop_flag.is_set():
            time.sleep(1)
            progress.update(task, advance=100 / TEST_DURATION)

    stop_flag.set()
    for t in master_threads + replica_threads:
        t.join()

    console.print("\n📊 [bold blue]Итоговая статистика[/bold blue]:")
    table = Table(show_header=True, header_style="bold yellow")
    table.add_column("Уровень")
    table.add_column("Операция")
    table.add_column("Количество")

    m = stats["master"]
    r = stats["replica"]
    table.add_row("Мастер", "INSERT", str(m["inserts"]))
    table.add_row("Мастер", "SELECT", str(m["selects"]))
    table.add_row("Мастер", "UPDATE", str(m["updates"]))
    table.add_row("Мастер", "DELETE", str(m["deletes"]))
    table.add_row("Мастер", "Сложные запросы", str(m["complex_queries"]))
    table.add_row("Мастер", "Ошибки", str(m["errors"]))
    table.add_row("Реплика", "SELECT", str(r["selects"]))
    table.add_row("Реплика", "Ошибки", str(r["errors"]))

    console.print(table)
    console.print(Panel.fit("[green]✅ Тест завершён успешно![/green]"))

if __name__ == "__main__":
    NUM_THREADS_MASTER = int(input("Введите количество потоков для мастера: "))
    NUM_THREADS_REPLICA = int(input("Введите количество потоков для реплики: "))
    TEST_DURATION = int(input("Введите длительность теста в секундах: "))
    run_stress_test()