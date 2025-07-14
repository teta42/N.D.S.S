from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Note
from django.conf import settings
from util.meilisearch import create_meilisearch_client

index_name = getattr(settings, "MEILISEARCH_INDEX_NAME", 'notes')

#TODO переделать под celery
@receiver(post_delete, sender=Note)
def delete_file_on_model_delete(sender, instance, **kwargs):
    if instance.content:
        instance.content.delete(save=False)

@receiver(post_save, sender=Note) #TODO Добавить проверку на публичность заметки
def loading_content_into_a_search_engine(sender, instance, created, **kwargs):
    if created:
        if instance.is_public:
            client = create_meilisearch_client()
            
            index = client.index(index_name)
            
            documents = {"id": instance.note_id, "content": instance.get_content_text}
            
            response = index.add_documents(documents)

            # Ожидаем завершения задачи
            client.wait_for_task(response.task_uid)
    else:
        #TODO переделать под celery
        print(f"Объект обновлён: {instance}")
