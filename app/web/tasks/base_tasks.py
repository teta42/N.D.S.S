import json
import logging
from celery import shared_task
from django.conf import settings
from botocore.exceptions import ClientError

from util.cache import wcache
from util.meilisearch import get_meilisearch_index
from util.minio_client import get_minio_client

logger = logging.getLogger("myapp")

# ----------- Redis -----------
def delete_from_cache(cache_key: str):
    cache = wcache()
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            cache.delete(cache_key)
            logger.info(f"[Cache] {cache_key} удалён из кэша.")
        else:
            logger.info(f"[Cache] {cache_key} не найден в кэше.")
    except Exception as e:
        logger.warning(f"[Cache] Ошибка при удалении из кэша: {e}")

def get_cached_content(cache_key: str):
    cache = wcache()
    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            try:
                cached_obj = json.loads(cached_data)
                return cached_obj.get("content")
            except Exception:
                logger.warning(f"[Cache] Не удалось десериализовать JSON для ключа {cache_key}")
        return None
    except Exception as e:
        logger.warning(f"[Cache] Ошибка получения данных из кэша: {e}")
        return None


# ----------- MinIO -----------
def delete_from_minio(note_id: str):
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
        logger.exception(f"[MinIO] Неизвестная ошибка: {e}")


# ----------- Meilisearch -----------
def delete_from_meilisearch(note_id: str):
    try:
        index = get_meilisearch_index()
        task = index.delete_documents([note_id])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Meilisearch] Документ {note_id} удалён.")
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка при удалении {note_id}: {e}")

def update_in_meilisearch(serialized_note: dict):
    try:
        index = get_meilisearch_index()
        doc = {"id": serialized_note["id"], "content": serialized_note["content"]}
        task = index.add_documents([doc])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Meilisearch] Документ {doc['id']} обновлён.")
    except Exception as e:
        logger.exception(f"[Meilisearch] Ошибка при обновлении документа {serialized_note['id']}: {e}")


# ----------- Celery задачи -----------

@shared_task
def delete_note_data(note_id: str):
    """
    Удаляет данные заметки из Redis, MinIO и Meilisearch.
    """
    cache_key = f"note:{note_id}"
    delete_from_cache(cache_key)
    delete_from_minio(note_id)
    delete_from_meilisearch(note_id)


@shared_task
def update_note_data_if_changed(note_id: str, serialized_note: dict):
    """
    Обновляет данные заметки, если content изменился.
    """
    cache_key = f"note:{note_id}"
    new_content = serialized_note.get("content")

    if new_content is None:
        logger.warning(f"[Update] Нет content в note {note_id}.")
        return

    cached_content = get_cached_content(cache_key)
    if cached_content == new_content:
        logger.info(f"[Update] Контент для note {note_id} не изменился.")
        return

    delete_from_cache(cache_key)
    update_in_meilisearch(serialized_note)


@shared_task
def update_private_note(note_id: str, serialized_note: dict):
    """
    Обновляет приватную заметку
    """
    cache_key = f"note:{note_id}"
    new_content = serialized_note.get("content")

    if new_content is None:
        logger.warning(f"[Update] Нет content в note {note_id}.")
        return

    cached_content = get_cached_content(cache_key)
    if cached_content == new_content:
        logger.info(f"[Update] Контент для note {note_id} не изменился.")
        return

    delete_from_cache(cache_key)