from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import Note
from util.meilisearch import create_meilisearch_client, index_name

#TODO переделать под celery
@receiver(post_delete, sender=Note)
def delete_file_on_model_delete(sender, instance, **kwargs):
    if instance.content:
        instance.content.delete(save=False)

@receiver(post_save, sender=Note)
def mymodel_post_save(sender, instance, created, **kwargs):
    if created:
        client = create_meilisearch_client()
        
        index = client.index(index_name)
        
        documents = {"id": instance.note_id, "content": instance.content}
        
        response = index.add_documents(documents)

        # Ожидаем завершения задачи
        client.wait_for_task(response['taskUid'])
    else:
        #TODO переделать под celery
        print(f"Объект обновлён: {instance}")
