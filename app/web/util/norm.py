def normalize_string(text: str) -> str:
    # Приводим к нижнему регистру и убираем пробелы по бокам
    cleaned = text.strip().lower()

    # Разбиваем по словам (разделитель — любые пробелы)
    words = cleaned.split()

    # Сортируем слова по Unicode-алфавиту
    sorted_words = sorted(words, key=lambda w: w.casefold())

    # Объединяем обратно в строку
    return ' '.join(sorted_words)
