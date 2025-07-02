from django.contrib import admin
from .models import Note, CustomUser

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('note_id', 'user', 'created_at', 'dead_line', 'only_authorized')
    list_filter = ('only_authorized', 'user')  # фильтры справа
    search_fields = ('note_id', 'content')  # поля для поиска
    ordering = ('-created_at',)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'is_staff', )
    ordering = ('username',)