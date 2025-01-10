from django.contrib.auth.forms import UserCreationForm
from .customuser import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'user_id', 'password')  # Добавьте нужные поля
