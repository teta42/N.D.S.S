from django.db import models

class Note(models.Model):
    note_id = models.CharField(max_length=7, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    read_only = models.BooleanField()   # 1 = чтение ; 0 = чтение и запись

    def __str__(self):
        return self.note_id     # Возвращает индефикатор заметки при выводе
    
    class Meta:
        ordering = ['-created_at']  # Сортировка по дате создания (новые заметки первыми)
        verbose_name = 'Заметка'     # Человекочитаемое имя модели в единственном числе
        verbose_name_plural = 'Заметки'  # Человекочитаемое имя модели во множественном числе
        db_table = 'note'            # Имя таблицы в базе данных
