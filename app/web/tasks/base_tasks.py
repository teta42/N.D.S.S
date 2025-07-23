import json
import logging
from celery import shared_task
from django.conf import settings
from botocore.exceptions import ClientError
from meilisearch.errors import MeilisearchApiError

from util.cache import wcache
from util.meilisearch import get_meilisearch_index
from util.minio_client import get_minio_client

logger = logging.getLogger("myapp")

# ----------- Helpers -----------
def extract_note_metadata(serialized_note: dict) -> tuple[str | None, bool | None]:
    """
    Извлекает note_id и is_public из сериализованной заметки.

    :param serialized_note: Словарь с полями заметки
    :return: Кортеж (note_id, is_public). Если поле отсутствует — None с логированием предупреждения.
    """
    note_id = serialized_note.get("note_id")
    if note_id is None:
        logger.warning("[Meilisearch] Отсутствует 'note_id' в serialized_note.")

    is_public = serialized_note.get("is_public")
    if is_public is None:
        logger.warning(f"[Meilisearch] Отсутствует 'is_public' в заметке {note_id or 'unknown'}.")

    return note_id, is_public


# ----------- Redis -----------
def delete_from_cache(cache_key: str) -> None:
    """
    Удаляет объект из Redis по ключу, если он существует.

    :param cache_key: Ключ в формате 'note:{note_id}'
    """
    cache = wcache()
    try:
        if cache.get(cache_key) is not None:
            cache.delete(cache_key)
            logger.info(f"[Cache] Ключ {cache_key} удалён из кэша.")
        else:
            logger.info(f"[Cache] Ключ {cache_key} не найден в кэше.")
    except Exception as e:
        logger.warning(f"[Cache] Ошибка при удалении из кэша: {e}")


def get_cached_content(cache_key: str) -> str | None:
    """
    Получает поле 'content' из сериализованной заметки, сохранённой в кэше Redis.

    :param cache_key: Ключ кэша
    :return: Строка контента или None
    """
    cache = wcache()
    try:
        cached_data = cache.get(cache_key)
        if cached_data is None:
            logger.debug(f"[Cache] Ключ {cache_key} отсутствует в кэше.")
            return None

        content = cached_data.get("content")
        if content is None:
            logger.warning(f"[Cache] В кэше по ключу {cache_key} отсутствует поле 'content'.")
        return content
    except Exception as e:
        logger.warning(f"[Cache] Ошибка получения данных из кэша по ключу {cache_key}: {e}")
        return None


# ----------- MinIO -----------
def delete_from_minio(note_id: str) -> None:
    """
    Удаляет файл заметки из MinIO-хранилища.

    :param note_id: Уникальный идентификатор заметки
    """
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    file_name = f"{note_id}.txt"

    if not bucket_name:
        logger.error("[MinIO] AWS_STORAGE_BUCKET_NAME не задан в настройках.")
        return

    try:
        minio_client = get_minio_client()
        minio_client.delete_object(Bucket=bucket_name, Key=file_name)
        logger.info(f"[MinIO] Файл {file_name} удалён из хранилища.")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            logger.warning(f"[MinIO] Файл {file_name} не найден.")
        else:
            logger.exception(f"[MinIO] Ошибка при удалении {file_name}: {e}")
    except Exception as e:
        logger.exception(f"[MinIO] Неизвестная ошибка при удалении {file_name}: {e}")


# ----------- Meilisearch -----------
def document_exists(index, note_id: str) -> bool:
    """
    Проверяет существование документа в Meilisearch по note_id.

    :param index: Объект индекса Meilisearch
    :param note_id: Идентификатор заметки
    :return: True если документ существует, иначе False
    """
    try:
        index.get_document(note_id)
        return True
    except MeilisearchApiError as e:
        if "document_not_found" in str(e):
            logger.info(f"[Meilisearch] Документ {note_id} не найден.")
            return False
        logger.exception(f"[Meilisearch] API-ошибка при проверке документа {note_id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"[Meilisearch] Неизвестная ошибка при проверке документа {note_id}: {e}")
        return False


def add_or_update_document(index, serialized_note: dict) -> None:
    """
    Добавляет или обновляет документ в Meilisearch.

    :param index: Объект индекса
    :param serialized_note: Данные заметки
    """
    note_id = extract_note_metadata(serialized_note)[0]
    doc = {
        "id": note_id,
        "content": serialized_note.get("content", "")
    }
    try:
        task = index.add_documents([doc])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Meilisearch] Документ {note_id} добавлен/обновлён.")
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка при добавлении/обновлении документа {note_id}: {e}")


def delete_from_meilisearch(note_id: str) -> None:
    """
    Удаляет документ из Meilisearch по note_id.

    :param note_id: Идентификатор заметки
    """
    try:
        index = get_meilisearch_index()
        task = index.delete_documents([note_id])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Meilisearch] Документ {note_id} удалён из индекса.")
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка при удалении документа {note_id}: {e}")


@shared_task
def update_meilisearch_document_if_public(serialized_note: dict) -> None:
    """
    Добавляет или удаляет документ из Meilisearch в зависимости от публичности.

    - Если is_public=True и документ отсутствует — добавляется.
    - Если is_public=False и документ присутствует — удаляется.

    :param serialized_note: Данные заметки
    """
    note_id, is_public = extract_note_metadata(serialized_note)
    if not note_id or is_public is None:
        return

    try:
        index = get_meilisearch_index()
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка получения индекса: {e}")
        return

    exists = document_exists(index, note_id)

    if is_public:
        if exists:
            logger.debug(f"[Meilisearch] Документ {note_id} уже существует — пропускаем.")
        else:
            logger.debug(f"[Meilisearch] Документ {note_id} отсутствует — добавляем.")
            add_or_update_document(index, serialized_note)
    else:
        if exists:
            logger.debug(f"[Meilisearch] Документ {note_id} приватен и существует — удаляем.")
            delete_from_meilisearch(note_id)
        else:
            logger.debug(f"[Meilisearch] Документ {note_id} приватен и отсутствует — пропускаем.")


# ----------- Celery задачи -----------
@shared_task
def delete_note_data(note_id: str) -> None:
    """
    Удаляет все связанные с заметкой данные:
    - из Redis (ключ note:{note_id})
    - из MinIO ({note_id}.txt)
    - из Meilisearch

    :param note_id: Уникальный идентификатор заметки
    """
    cache_key = f"note:{note_id}"
    delete_from_cache(cache_key)
    delete_from_minio(note_id)
    delete_from_meilisearch(note_id)


@shared_task
def update_note_data_if_changed(note_id: str, serialized_note: dict) -> None:
    """
    Проверяет и обновляет данные заметки, #если изменился её контент.
    Также обновляет индекс Meilisearch в зависимости от публичности.

    :param note_id: Уникальный идентификатор заметки
    :param serialized_note: Сериализованная заметка
    """
    cache_key = f"note:{note_id}"
    new_content = serialized_note.get("content")

    if new_content is None:
        logger.warning(f"[Update] Контент отсутствует в заметке {note_id}.")
        return

    cached_content = get_cached_content(cache_key)

    # Можно раскомментировать для оптимизации
    # if cached_content == new_content:
    #     logger.info(f"[Update] Контент заметки {note_id} не изменился — пропуск.")
    #     return

    if cached_content is not None:
        delete_from_cache(cache_key)

    update_meilisearch_document_if_public(serialized_note)
    logger.info(f"[Update] Заметка {note_id} обновлена.")
