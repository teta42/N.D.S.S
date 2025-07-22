import json
import logging
from celery import shared_task
from django.conf import settings
from botocore.exceptions import ClientError

from util.cache import wcache
from util.meilisearch import get_meilisearch_index
from util.minio_client import get_minio_client

logger = logging.getLogger("myapp")

# ----------- Utils -----------
def get_note_id(serialized_note: dict) -> str | None:
    """
    Извлекает note_id из сериализованной заметки.

    :param serialized_note: сериализованная заметка
    :return: note_id или None
    """
    note_id = serialized_note.get("note_id")
    if note_id is None:
        logger.warning("[Meilisearch] Отсутствует 'note_id' в serialized_note.")
    return note_id

def get_is_public(serialized_note: dict) -> bool | None:
    """
    Извлекает флаг is_public из сериализованной заметки.

    :param serialized_note: сериализованная заметка
    :return: is_public или None
    """
    is_public = serialized_note.get("is_public")
    if is_public is None:
        note_id = serialized_note.get("note_id", "unknown")
        logger.warning(f"[Meilisearch] Отсутствует 'is_public' в заметке {note_id}.")
    return is_public

def get_meilisearch_index_safe():
    """
    Безопасное получение индекса Meilisearch.

    :return: индекс или None в случае ошибки
    """
    try:
        return get_meilisearch_index()
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка получения индекса: {e}")
        return None

def document_exists(index, note_id: str) -> bool:
    """
    Проверяет существование документа в Meilisearch по note_id.

    :param index: индекс Meilisearch
    :param note_id: идентификатор заметки
    :return: True если существует, иначе False
    """
    try:
        _ = index.get_document(note_id, fields=["id"])
        return True
    except Exception as e:
        if "document not found" in str(e).lower():
            return False
        logger.exception(f"[Meilisearch] Ошибка при проверке документа {note_id}: {e}")
        return False

def add_or_update_document(index, serialized_note: dict):
    """
    Добавляет или обновляет документ в Meilisearch.

    :param index: индекс Meilisearch
    :param serialized_note: сериализованная заметка
    """
    note_id = get_note_id(serialized_note)
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


# ----------- Redis -----------
def delete_from_cache(cache_key: str):
    """
    Удаляет запись из Redis-кэша по ключу.

    :param cache_key: ключ кэша
    """
    cache = wcache()
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            cache.delete(cache_key)
            logger.info(f"[Cache] Ключ {cache_key} удалён из кэша.")
        else:
            logger.info(f"[Cache] Ключ {cache_key} не найден в кэше.")
    except Exception as e:
        logger.warning(f"[Cache] Ошибка при удалении из кэша: {e}")

def get_cached_content(cache_key: str):
    """
    Получает содержимое заметки из кэша Redis по ключу.

    :param cache_key: ключ кэша
    :return: контент или None
    """
    cache = wcache()
    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            try:
                cached_obj = json.loads(cached_data)
                return cached_obj.get("content")
            except Exception:
                logger.warning(f"[Cache] Не удалось десериализовать JSON по ключу {cache_key}.")
        return None
    except Exception as e:
        logger.warning(f"[Cache] Ошибка получения данных из кэша: {e}")
        return None


# ----------- MinIO -----------
def delete_from_minio(note_id: str):
    """
    Удаляет файл заметки из MinIO-хранилища.

    :param note_id: идентификатор заметки
    """
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    file_name = f"{note_id}.txt"

    if not bucket_name:
        logger.error("[MinIO] AWS_STORAGE_BUCKET_NAME не задан в настройках.")
        return

    try:
        minio_client = get_minio_client()
        minio_client.delete_object(Bucket=bucket_name, Key=file_name)
        logger.info(f"[MinIO] Файл {file_name} удалён.")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            logger.warning(f"[MinIO] Файл {file_name} не найден.")
        else:
            logger.exception(f"[MinIO] Ошибка при удалении {file_name}: {e}")
    except Exception as e:
        logger.exception(f"[MinIO] Неизвестная ошибка при удалении {file_name}: {e}")


# ----------- Meilisearch -----------
def delete_from_meilisearch(note_id: str):
    """
    Удаляет документ из Meilisearch по note_id.

    :param note_id: идентификатор заметки
    """
    try:
        index = get_meilisearch_index_safe()
        task = index.delete_documents([note_id])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Meilisearch] Документ {note_id} удалён.")
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка при удалении {note_id}: {e}")

@shared_task
def update_meilisearch_document_if_public(serialized_note: dict):
    """
    Обновляет или добавляет документ в Meilisearch, если заметка публичная.

    :param serialized_note: сериализованная заметка
    """
    note_id = get_note_id(serialized_note)
    if not note_id:
        return

    is_public = get_is_public(serialized_note)
    if is_public is None:
        return

    if not is_public:
        logger.info(f"[Meilisearch] Заметка {note_id} приватна — пропускаем обновление в поиске.")
        return

    index = get_meilisearch_index_safe()
    if index is None:
        return

    exists = document_exists(index, note_id)
    if exists:
        logger.debug(f"[Meilisearch] Документ {note_id} существует — обновляем.")
    else:
        logger.debug(f"[Meilisearch] Документ {note_id} отсутствует — добавляем.")

    add_or_update_document(index, serialized_note)


# ----------- Celery задачи -----------

@shared_task
def delete_note_data(note_id: str):
    """
    Удаляет все связанные с заметкой данные:
      - из Redis (по ключу "note:{note_id}")
      - из MinIO-хранилища (файл {note_id}.txt)
      - из Meilisearch (если он был там)

    :param note_id: идентификатор заметки
    """
    cache_key = f"note:{note_id}"
    delete_from_cache(cache_key)
    delete_from_minio(note_id)
    delete_from_meilisearch(note_id)

def update_note_if_content_changed(note_id: str, serialized_note: dict) -> bool:
    """
    Обновляет данные заметки, если изменился её контент. 
    Если заметка публичная, то обновляет Meilisearch.

    :param note_id: идентификатор заметки
    :param serialized_note: сериализованная заметка
    :param is_public: является ли заметка публичной
    :return: True если обновление произошло, иначе False
    """
    cache_key = f"note:{note_id}"
    new_content = serialized_note.get("content")

    if new_content is None:
        logger.warning(f"[Update] Контент отсутствует в заметке {note_id}.")
        return False

    cached_content = get_cached_content(cache_key)
    if cached_content == new_content:
        logger.info(f"[Update] Контент заметки {note_id} не изменился — пропуск обновления.")
        return False

    delete_from_cache(cache_key)
    update_meilisearch_document_if_public(serialized_note)

    return True

@shared_task
def update_note_data_if_changed(note_id: str, serialized_note: dict):
    """
    Celery-задача: проверяет и обновляет данные заметки, если изменился её контент.
    Если заметка публичная, то обновляется индекс Meilisearch.

    :param note_id: идентификатор заметки
    :param serialized_note: сериализованная заметка
    """
    updated = update_note_if_content_changed(note_id, serialized_note)
    if updated:
        logger.info(f"[Update] Заметка {note_id} обновлена.")
