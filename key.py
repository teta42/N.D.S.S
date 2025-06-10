import secrets
import string
from app.models import Note, CustomUser

def generate_random_key(length=16):
    # Определяем возможные символы: большие и малые буквы, а также цифры
    lowercase_letters = string.ascii_lowercase  # Маленькие буквы
    uppercase_letters = string.ascii_uppercase  # Большие буквы
    digits = string.digits                      # Цифры

    characters = lowercase_letters + uppercase_letters + digits

    random_key = ''

    # Генерируем случайные символы до достижения заданной длины
    for _ in range(length):
        random_character = secrets.choice(characters)
        random_key += random_character

    return random_key

if __name__ == '__main__':
    for a in range(10):
        key = generate_random_key(7)
        print(key)



def create_id():
    while True:
        key = str(generate_random_key(7)) # Генерируем ключ
        
        # Проверяем его уникальность
        note = Note.objects.filter(note_id=key).exists()
        user = CustomUser.objects.filter(user_id=key).exists()
        
        if note == False and user == False:
            break
        
        print('Это не уникальный ключ')
        
    return key