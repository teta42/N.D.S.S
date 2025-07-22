from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Note
import logging
from util.meilisearch import get_meilisearch_index
from tasks.base_tasks import delete_note_data, update_note_data_if_changed
from .serializer import NoteSerializer

logger = logging.getLogger("myapp")

@receiver(post_delete, sender=Note)
def delete_file_on_model_delete(sender, instance, **kwargs):
    if instance.content:
        logger.debug(f"The note content was removed from the object storage {instance.note_id}")
        delete_note_data.delay(instance.note_id)

@receiver(post_save, sender=Note)
def loading_content_into_a_search_engine(sender, instance, created, **kwargs):
    if created:
        if instance.is_public:
            
            index = get_meilisearch_index()
            
            documents = {"id": instance.note_id, "content": instance.get_content_text}
            
            response = index.add_documents(documents)

            # Ожидаем завершения задачи
            index.wait_for_task(response.task_uid)
            
            logger.debug(f"The content of this note {instance.note_id} has been added to the search engine.")
    else:
        if instance.is_public:
            serializer = NoteSerializer(instance)
            update_note_data_if_changed.delay(instance.note_id, serializer.data)
