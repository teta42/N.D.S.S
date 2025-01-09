from service_accounts.models import Password_Blocker
from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    model = CustomUser
    list_display = ['username', 'email', 'user_id', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Password_Blocker)