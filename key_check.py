from key_gen import generate_random_key as grk
from card_manager.models import Note
from service_accounts.models import CustomUser

def create_id():
    while True:
        key = str(grk(7)) # Генерируем ключ
        
        # Проверяем его уникальность
        note = Note.objects.filter(note_id=key).exists()
        user = CustomUser.objects.filter(user_id=key).exists()
        
        if note == False and user == False:
            break
        
        print('Это не уникальный ключ')
        
    return key