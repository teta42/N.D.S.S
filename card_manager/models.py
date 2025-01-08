from django.db import models
from service_accounts.models import CustomUser

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

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных

    def save(self, *args, we_create:bool=True ,**kwargs):
        if we_create: # True создаём, False обновляем
            from key_check import create_id
            self.note_id = create_id()
        
        super().save(*args, **kwargs)
            
    def increase_reads(self):
        self.read_count += 1
        self.save(we_create=False)