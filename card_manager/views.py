from django.http import JsonResponse
from django.shortcuts import render
import json
from .models import Note
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from check_life import is_valid
from service_accounts.customuser import CustomUser

def home(request):
    return render(request, 'home.html')

@ensure_csrf_cookie
def create_note(request):
    if request.method == 'POST':
        # Получаем данные из тела запроса
        body = request.body
        data = json.loads(body)
        # Достаём нужные данные
        note_content = data.get('content')
        read_only = data.get('read_only')
        dead_line = data.get('dead_line')
        one_read = data.get('one_read')
        only_auth = data.get('only_auth', False)

        # Приводим данные к нормальному виду
        mode = (read_only == "read") # Проверка на истеность выражения
            
        if request.user.is_authenticated: 
            user = CustomUser.objects.get(user_id=request.user.pk)
            # Создаём объект
            note = Note.objects.create_note(user=user,
                        content=note_content, read_only=mode, 
                        dead_line=dead_line, deletion_on_first_reading=one_read, 
                        only_authorized=only_auth)
            
            return JsonResponse({'note_id': str(note.note_id)})
        else:
            user = CustomUser.objects.get(username='root')
            # Создаём объект
            note = Note.objects.create_note(user=user,
                        content=note_content, read_only=mode, 
                        dead_line=dead_line, deletion_on_first_reading=one_read,
                        only_authorized=only_auth)
            
            return JsonResponse({'note_id': str(note.note_id)})
        
    elif request.method == 'GET':
        return render(request, 'create_note.html')
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@ensure_csrf_cookie
def read_note_html(request, note_id):
    # Отображение HTML-страницы с заметкой
    note = get_object_or_404(Note, note_id=note_id)
    return render(request, 'read_note.html')

@ensure_csrf_cookie
def read_note(request, note_id):
    if request.method == 'GET':
        note = get_object_or_404(Note, note_id=note_id) 
        # Возвращение 404 если записки с таким id нет, если нет то возврощяем объект
        
        if not note.is_valid(user=(request.user.is_authenticated)):
            return JsonResponse({'error': 'Page not found'}, status=404)
        
        mod = 'read' if note.read_only else 'write'
        
        # Создаем словарь с данными
        response_data = {
            'created_at': note.created_at,
            'content': note.content,
            'mod': mod,
            'dead_line': note.dead_line,
        }

        # Увеличиваем счётчик прочтений на 1
        note.increase_reads()
        
        # Возвращаем JsonResponse с данными
        return JsonResponse(response_data, status=200)
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

def write_note(request, note_id):
    if request.method == 'POST':
        note = get_object_or_404(Note, note_id=note_id) 
        # Возвращение 404 если записки с таким id нет, если нет то возврощяем объект
        if note.read_only == True:
            return JsonResponse({'error': 'Записка только на чтение'}, status=400)
        # Получаем данные из тела запроса
        body = request.body
        data = json.loads(body)
        # Достаём нужные данные
        new_content = data.get('content')
        
        # Изменяем модель
        note.content = new_content
        note.save()
        
        return JsonResponse({'status': 200}, status=200)
    elif request.method == 'GET':
        return render(request, 'write_note.html')
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
def page_404(request):
    if request.method == "GET":
        return render(request, '404.html')
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)