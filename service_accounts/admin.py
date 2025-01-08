from service_accounts.models import Password_Blocker
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_id', 'is_staff')
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {
            'fields': ('user_id',),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Password_Blocker)