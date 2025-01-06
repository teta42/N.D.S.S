from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Password_Blocker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    incorrect_password_counter = models.IntegerField(default=0)
    unlock_date = models.DateTimeField(default='2007-09-23 12:53:42.424242')
    next_blocking_for_how_long = models.IntegerField(default=24) # Указание времени для следующей блокировки в часах
    
    def increase_next_lock(self):
        rev = (24, 168, 720, 876000)
        for i in range(len(rev)):
            if self.next_blocking_for_how_long == rev[i]:
                if i < 3:
                    self.next_blocking_for_how_long = rev[i+1]
                    self.save()
    def __str__(self):
        return self.user.username
    
    class meta():
        db_table = 'account_block'
        verbose_name = 'Блокировка аккаунта'
        verbose_name_plural = 'Блокировки аккаунтов'
    
@receiver(post_save, sender=User)
def create_or_update_password_blocker(sender, instance, created, **kwargs):
    if created:
        Password_Blocker.objects.create(user=instance)
    else:
        instance.password_blocker.save()