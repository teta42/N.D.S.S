from django.contrib import admin
from .models import Note

class NoteAdmin(admin.ModelAdmin):
    list_display = ('note_id', 'user_id', 'read_count')
    search_fields = ('user_id', 'content') # 'title'
    list_filter = ('created_at',)
    ordering = ('-created_at',)

admin.site.register(Note,  NoteAdmin)