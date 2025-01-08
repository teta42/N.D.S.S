from .models import CustomUser, Password_Blocker
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_or_update_password_blocker(sender, instance, created, **kwargs):
    if created:
        Password_Blocker.objects.create(user=instance)
    else:
        instance.password_blocker.save()