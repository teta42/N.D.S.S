import logging
from functools import lru_cache
from typing import Optional

import meilisearch
from meilisearch.errors import MeilisearchApiError, MeilisearchCommunicationError

from django.conf import settings
import meilisearch.index

logger = logging.getLogger("myapp")

@lru_cache(maxsize=1)
def create_meilisearch_client() -> meilisearch.Client:
    """
    Создаёт и возвращает кэшированный Meilisearch клиент.

    Получает конфигурацию из Django settings: URL, API-ключ и имя индекса.
    Также гарантирует, что индекс существует и настроен.
    """
    url: Optional[str] = getattr(settings, "MEILISEARCH_URL", None)
    api_key: Optional[str] = getattr(settings, "MEILISEARCH_API_KEY", None)

    if not url:
        logger.error("MEILISEARCH_URL is not defined in settings.")
        raise ValueError("MEILISEARCH_URL is required")

    try:
        client = meilisearch.Client(url, api_key)
        logger.info("Meilisearch client successfully created.")
        return client
    except Exception as e:
        logger.exception("Failed to create Meilisearch client.")
        raise e


@lru_cache(maxsize=1)
def get_meilisearch_index(index_name:str=None) -> meilisearch.index:
    """
    Возвращает объект индекса Meilisearch.

    Если индекс не существует, создаёт его.
    Также проверяет и при необходимости применяет настройки (searchable и displayed attributes).
    """
    client = create_meilisearch_client()
    if index_name == None:
        index_name: str = getattr(settings, "MEILISEARCH_INDEX_NAME", "notes")

    try:
        index = client.index(index_name)

        # Проверим, существует ли индекс
        try:
            current_settings = index.get_settings()
            logger.debug(f"Current Meilisearch index settings: {current_settings}")
        except MeilisearchApiError:
            logger.warning(f"Index '{index_name}' does not exist. Creating it.")
            task = client.create_index(uid=index_name, options={"primaryKey": "id"})
            client.wait_for_task(task.task_uid)
            index = client.index(index_name)
            current_settings = index.get_settings()

        # Применим настройки, только если они отличаются
        expected_searchable = ["id", "content"]
        expected_displayed = ["id", "content"]

        update_needed = (
            current_settings.get("searchableAttributes") != expected_searchable or
            current_settings.get("displayedAttributes") != expected_displayed
        )

        if update_needed:
            logger.info("Updating Meilisearch index settings...")
            task1 = index.update_searchable_attributes(expected_searchable)
            index.wait_for_task(task1.task_uid)

            task2 = index.update_displayed_attributes(expected_displayed)
            index.wait_for_task(task2.task_uid)
            logger.info("Meilisearch index settings updated.")
        else:
            logger.info("Meilisearch index already has correct settings. Skipping update.")

        return index

    except (MeilisearchApiError, MeilisearchCommunicationError) as e:
        logger.exception("Failed to initialize or configure Meilisearch index.")
        raise e
    except Exception as e:
        logger.exception("Unexpected error while getting Meilisearch index.")
        raise e
