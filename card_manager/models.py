from django.db import models
from key_gen import generate_random_key as grk

class Note(models.Model):
    note_id = models.CharField(max_length=7, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    read_only = models.BooleanField(default=True)  
    # 1 = чтение ; 0 = чтение и запись
    dead_line = models.DateTimeField()

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных

    def save(self, *args, **kwargs):
        exist = Note.objects.filter(note_id=self.note_id).exists()
        if not self.note_id:
            key = self._create_note_id()
            self.note_id = key
        
        super().save(*args, **kwargs)
        
    def _create_note_id(self):
        while True:
            key = grk(7) # генерация ключа длиной в 7
            if_key = Note.objects.filter(note_id=key).exists()
            # Проверка есть ли уже такой ключ
            if if_key == False:
                return key
            print("Созданный ключ уже есть, пересоздаю...")