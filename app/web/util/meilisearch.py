import meilisearch
from django.conf import settings
from meilisearch.errors import MeiliSearchApiError

def create_meilisearch_client() -> meilisearch.Client:
    url = getattr(settings, "MEILISEARCH_URL", None)
    api_key = getattr(settings, "MEILISEARCH_API_KEY", None)
    index_name = getattr(settings, "MEILISEARCH_INDEX_NAME", 'notes')

    client = meilisearch.Client(url, api_key)

    # Проверяем наличие индекса
    try:
        index = client.index(index_name)
        index.get_raw_info()
    except MeiliSearchApiError:
        client.create_index(uid=index_name, options={"primaryKey": "id"})
        index = client.index(index_name)

    # Устанавливаем поля
    task1 = index.update_searchable_attributes(["content"])
    index.wait_for_task(task1.task_uid)

    task2 = index.update_displayed_attributes(["id"])
    index.wait_for_task(task2.task_uid)

    return client
