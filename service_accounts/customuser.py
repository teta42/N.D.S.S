from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, email, user_id=None, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        
        if user_id is None:
            from key_check import create_id
            user_id = create_id()
        
        email = self.normalize_email(email)
        user = self.model(email=email, user_id=user_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        from key_check import create_id
        user_id = create_id()
        return self.create_user(email, user_id=user_id, password=password, **extra_fields)


class CustomUser(AbstractUser):
    user_id = models.CharField(max_length=7, primary_key=True)

    objects = CustomUserManager()

    def __str__(self):
        return self.username
    
    class Meta():
        db_table = 'customuser'
        verbose_name = 'Мой пользователь'
        verbose_name_plural = 'Мои пользователи'