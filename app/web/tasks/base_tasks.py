import json
from celery import shared_task
from util.cache import wcache
from util.meilisearch import get_meilisearch_index
from util.minio_client import get_minio_client
from botocore.exceptions import ClientError
import logging
from django.conf import settings

logger = logging.getLogger("myapp")


@shared_task
def delete_note_data(note_id: str):
    """
    Удаляет:
    - Кэш из write_cache
    - Файл {note_id}.txt из MinIO
    - Документ note_id из Meilisearch
    """
    cache_key = f"note:{note_id}"
    bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    file_name = f"{note_id}.txt"

    cache = wcache()

    # Удаление из write_cache
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            cache.delete(cache_key)
            logger.info(f"[Delete] Note {note_id} удалён из write_cache.")
        else:
            logger.info(f"[Delete] Note {note_id} не найден в write_cache.")
    except Exception as e:
        logger.warning(f"[Delete] Ошибка при удалении из кэша: {e}")

    # Удаление из MinIO
    if not bucket_name:
        logger.error("[Delete] AWS_STORAGE_BUCKET_NAME не задан в настройках.")
    else:
        try:
            minio_client = get_minio_client()
            minio_client.delete_object(Bucket=bucket_name, Key=file_name)
            logger.info(f"[Delete] Файл {file_name} удалён из MinIO.")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                logger.warning(f"[Delete] Файл {file_name} не найден в MinIO.")
            else:
                logger.exception(f"[Delete] Ошибка при удалении {file_name} из MinIO: {e}")
        except Exception as e:
            logger.exception(f"[Delete] Неизвестная ошибка при работе с MinIO: {e}")

    # Удаление из Meilisearch
    try:
        index = get_meilisearch_index("notes")
        # Метод принимает список id для удаления
        task = index.delete_documents([note_id])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Delete] Документ {note_id} удалён из Meilisearch.")
    except Exception as e:
        logger.exception(f"[Delete] Ошибка при удалении {note_id} из Meilisearch: {e}")


@shared_task
def update_note_data_if_changed(note_id: str, serialized_note: dict):
    """
    Сравнивает serialized_note['content'] с версией из write_cache.
    Если отличаются — удаляет кэш и обновляет документ в Meilisearch.
    """
    cache_key = f"note:{note_id}"
    new_content = serialized_note.get("content")

    if new_content is None:
        logger.warning(f"[Update] Нет content в данных для note {note_id}.")
        return

    cache = wcache()

    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            # Десериализуем JSON в словарь
            try:
                cached_obj = json.loads(cached_data)
                cached_content = cached_obj.get("content")
            except Exception:
                logger.warning(f"[Update] Не удалось десериализовать данные из write_cache для {note_id}")
                cached_content = None
        else:
            cached_content = None
    except Exception as e:
        logger.warning(f"[Update] Ошибка получения из write_cache: {e}")
        cached_content = None

    if cached_content == new_content:
        logger.info(f"[Update] Контент для note {note_id} не изменился. Обновление не требуется.")
        return

    # Контент изменился: удаляем из кэша
    try:
        cache.delete(cache_key)
        logger.info(f"[Update] Удалён из write_cache: {cache_key}")
    except Exception as e:
        logger.warning(f"[Update] Ошибка удаления из кэша: {e}")

    # Обновление в Meilisearch (перезапись документа)
    try:
        index = get_meilisearch_index("notes")

        doc_for_index = {
            "id": serialized_note["id"],
            "content": serialized_note["content"],
        }
        task = index.add_documents([doc_for_index])
        index.wait_for_task(task.task_uid)
        logger.info(f"[Update] Документ {note_id} обновлён в Meilisearch.")
    except Exception as e:
        logger.exception(f"[Update] Ошибка при обновлении документа {note_id} в Meilisearch: {e}")
