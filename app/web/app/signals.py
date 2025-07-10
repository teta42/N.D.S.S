from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Note

@receiver(post_delete, sender=Note)
def delete_file_on_model_delete(sender, instance, **kwargs):
    if instance.content:
        instance.content.delete(save=False)
