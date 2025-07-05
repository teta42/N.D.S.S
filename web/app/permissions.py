from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Пользователь может редактировать/удалять объект, только если он его владелец.
    GET, HEAD, OPTIONS — доступны всем.
    """

    def has_object_permission(self, request, view, obj):
        # Разрешаем чтение всем
        if request.method in permissions.SAFE_METHODS:
            return True

        # Для PUT, PATCH, DELETE проверяем, является ли пользователь владельцем
        return obj.user == request.user