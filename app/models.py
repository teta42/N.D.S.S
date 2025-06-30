from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext as _

class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, user_id=None, password=None, **extra_fields):
        if user_id is None:
            from key import create_id
            user_id = create_id()

        if email != None:
            email = self.normalize_email(email)
        user = self.model(email=email, user_id=user_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        from key import create_id
        user_id = create_id()
        return self.create_user(email, user_id=user_id, password=password, **extra_fields)


class CustomUser(AbstractUser):
    user_id = models.CharField(max_length=7, primary_key=True)
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
                    dead_line:str, only_authorized:bool, 
                    read_only:bool=True, to_comment:str=None) -> object:
        
        # Создание id
        from key import create_id
        id = create_id()
        
        note = self.model(note_id=id,
                          user=user, content=content, read_only=read_only, 
                    dead_line=dead_line,
                    only_authorized=only_authorized, to_comment=to_comment)
        
        note.save(using=self._db)
        return note

class Note(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='note')
    note_id = models.CharField(max_length=7, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    read_only = models.BooleanField(default=True)  
    # 1 = чтение ; 0 = чтение и запись
    dead_line = models.DateTimeField()
    only_authorized = models.BooleanField(default=False)
    # False Всем True только авторизованным
    to_comment = models.ForeignKey('self', on_delete=models.CASCADE, related_name='comments', null=True, db_index=True)
    
    objects = NoteManager()

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных