from django.http import JsonResponse
from django.shortcuts import render, redirect
import json
from .models import Note
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from service_accounts.customuser import CustomUser

def get_notes(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Вы не авторизованы"}, status=401)

    user = get_object_or_404(CustomUser, pk=request.user.user_id)
    notes = user.note.all()

    # Преобразование заметок в список словарей
    notes_list = [
        {
            'id': note.note_id,
            'content': note.content,
            'created_at': note.created_at,
            'mod': ('read' if note.read_only else 'write'),
            'dead_line': note.dead_line,
        }
        for note in notes
    ]

    return JsonResponse({'object': notes_list}, status=200)
        
def home(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    elif request.user.is_authenticated:
        return render(request, 'home.html')
    else:
        return redirect('aut')
        # return HttpResponse('Вы не авторизованы')

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
            
            return JsonResponse({'note_id': str(note.note_id)}, status=201)
        else:
            user = CustomUser.objects.get(username='anonymous')
            # Создаём объект
            note = Note.objects.create_note(user=user,
                        content=note_content, read_only=mode, 
                        dead_line=dead_line, deletion_on_first_reading=one_read,
                        only_authorized=only_auth)
            
            return JsonResponse({'note_id': str(note.note_id)}, status=201)
        
    elif request.method == 'GET':
        return render(request, 'create_note.html')
    else:
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)

@ensure_csrf_cookie
def read_note_html(request, note_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    # Отображение HTML-страницы с заметкой
    note = get_object_or_404(Note, note_id=note_id)
    return render(request, 'read_note.html')

@ensure_csrf_cookie
def read_note(request, note_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
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

def write_note(request, note_id):
    if request.method == 'PUT':
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
    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    return render(request, '404.html')