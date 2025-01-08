from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    user_id = models.CharField(max_length=7, primary_key=True)

    def save(self, *args, we_create:bool=False ,**kwargs):
        if we_create: # True создаём, False обновляем
            from key_check import create_id
            self.user_id = create_id()
        
        self.set_password(self.password)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
    
    class Meta():
        db_table = 'customuser'
        verbose_name = 'Мой пользователь'
        verbose_name_plural = 'Мои пользователи'