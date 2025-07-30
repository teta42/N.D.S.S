from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext as _
from datetime import datetime
from django.utils import timezone
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
import logging

INFINITY = timezone.make_aware(datetime(9999, 12, 31))

logger = logging.getLogger("myapp")

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, user_id=None, password=None, **extra_fields):
        if user_id is None:
            from util.key import get_key_from_sidecar
            user_id = get_key_from_sidecar()

        if email != None:
            email = self.normalize_email(email)
        user = self.model(email=email, user_id=user_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        from util.key import get_key_from_sidecar
        user_id = get_key_from_sidecar()
        return self.create_user(email, user_id=user_id, password=password, **extra_fields)


class CustomUser(AbstractUser):
    user_id = models.CharField(primary_key=True)
    email = models.EmailField(_('email address'), blank=True, null=True, unique=False)
    
    objects = CustomUserManager()

    def __str__(self):
        return self.username
    
    class Meta():
        db_table = 'customuser'
        verbose_name = 'Мой пользователь'
        verbose_name_plural = 'Мои пользователи'
        


class NoteManager(BaseUserManager):
    def create_note(self, user:object, content:str, 
                    only_authorized:bool, 
                    to_comment:str=None, dead_line:str=INFINITY,
                    burn_after_read:bool=False, is_public:bool=False) -> object:
        
        # Создание id
        from util.key import get_key_from_sidecar
        id = get_key_from_sidecar()
        
        is_burned = False
        
        content = ContentFile(content.encode("utf-8"), name=f"{id}.txt")
        
        note = self.model(note_id=id,user=user, 
                          content=content,
                          dead_line=dead_line,only_authorized=only_authorized, 
                          to_comment=to_comment, burn_after_read=burn_after_read, is_burned=is_burned,
                          is_public=is_public)
        
        note.save(using=self._db)
        return note

class Note(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='note')
    note_id = models.CharField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.FileField(upload_to='', storage=S3Boto3Storage())
    dead_line = models.DateTimeField(default=INFINITY)
    only_authorized = models.BooleanField(default=False)
    # False Всем True только авторизованным
    to_comment = models.ForeignKey('self', on_delete=models.CASCADE, related_name='comments', null=True, db_index=True)
    burn_after_read = models.BooleanField(default=False)
    is_burned = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    objects = NoteManager()

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    @property
    def get_content_text(self) -> str:
        try:
            if not self.content:
                return ""
            with self.content.open('r') as f:
                return f.read()  # уже str
        except Exception as e:
            logger.debug(f"[read error] {e}")
            return ''


    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных