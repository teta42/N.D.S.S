from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import exceptions

from django.contrib.auth import login, logout

from .models import Note
from .serializer import (
    NoteSerializer,
    RegisterSerializer,
    LoginSerializer,
    UserUpdateSerializer,
)


# Работа с заметками
class NoteAPI(ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Note.objects.filter(dead_line__gt=timezone.now())

    def get_queryset(self):
        user = self.request.user
        if (user and user.is_authenticated):
            # Список только своих активных заметок
            return Note.objects.filter(user=user, dead_line__gt=timezone.now())
        else:
            return Note.objects.filter(dead_line__gt=timezone.now()).filter(only_authorized=False)

    def get_object(self):
        user = self.request.user
        note_id = self.kwargs['pk']
        note = Note.objects.get(pk=note_id)

        # Проверка: актуальность заметки
        if note.dead_line <= timezone.now():
            raise exceptions.NotFound("Note has expired.")

        # Проверка доступа к конкретной заметке
        if note.only_authorized:
            if not (user and user.is_authenticated):
                raise exceptions.PermissionDenied("This note is for authorized users only.")

        return note


# Регистрация пользователя
class RegView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return Response(
                {"message": "Пользователь успешно создан"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Авторизация пользователя
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            user = serializer.validated_data["user"]
            login(request, user)
            return Response({"message": "Вход выполнен успешно"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Incorrect authorization data"}, status=status.HTTP_400_BAD_REQUEST)


# Выход из аккаунта
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logout(request)
        return Response({"message": "Выход выполнен успешно"}, status=status.HTTP_200_OK)


class UpdateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Полное обновление: все поля обязательны (кроме тех, что указаны как required=False)
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=False  # Полное обновление
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        # Частичное обновление: только указанные поля
        serializer = UserUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Удаление аккаунта
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "Аккаунт удален"}, status=status.HTTP_204_NO_CONTENT)