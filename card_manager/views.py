from django.http import JsonResponse
import json
from .models import Note

def create_note(request):
    if request.method == 'POST':
        # Получаем данные из тела запроса
        body = request.body
        data = json.loads(body)
        # Достаём нужные данные
        note_content = data.get('content')
        read_only = data.get('read_only')
        
        note = Note(content=note_content, read_only=read_only)
        note.save()
        
        return JsonResponse({'message': 'Заметка создана!'})
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)