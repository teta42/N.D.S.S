from django.db import models
from service_accounts.models import CustomUser
from django.contrib.auth.models import BaseUserManager

class NoteManager(BaseUserManager):
    def create_note(self, user:object, content:str, read_only:bool, 
                    dead_line:str, deletion_on_first_reading:bool, only_authorized:bool) -> object:
        dfr = deletion_on_first_reading
        
        # Создание id
        from key_check import create_id
        id = create_id()
        
        note = self.model(note_id=id,
                          user=user, content=content, read_only=read_only, 
                    dead_line=dead_line, deletion_on_first_reading=dfr,
                    only_authorized=only_authorized)
        
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
    read_count = models.PositiveIntegerField(default=0)
    deletion_on_first_reading = models.BooleanField(default=False)
    only_authorized = models.BooleanField(default=False)
    # False Всем True только авторизованным
    
    objects = NoteManager()

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных
        
    def increase_reads(self):
        self.read_count += 1
        self.save()
    
    def is_valid(self, user:bool) -> bool:
        from check_life import is_valid
        return is_valid(self, user)