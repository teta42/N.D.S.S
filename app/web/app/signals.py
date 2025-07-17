from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Note
import logging
from util.meilisearch import get_meilisearch_index

logger = logging.getLogger("myapp")

#TODO переделать под celery
@receiver(post_delete, sender=Note)
def delete_file_on_model_delete(sender, instance, **kwargs):
    if instance.content:
        logger.debug(f"The note content was removed from the object storage {instance.note_id}")
        instance.content.delete(save=False)

@receiver(post_save, sender=Note) #TODO Добавить проверку на публичность заметки
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
        #TODO переделать под celery
        logger.debug(f"Объект обновлён: {instance.note_id}")
