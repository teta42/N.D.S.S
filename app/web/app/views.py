from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import exceptions
from django.shortcuts import get_object_or_404
from .permissions import IsOwnerOrReadOnly

from django.contrib.auth import login, logout

from .pagination import CommentPagination

from .models import Note
from .serializer import (
    NoteSerializer,
    RegisterSerializer,
    LoginSerializer,
    UserUpdateSerializer,
)


class RandomNote(APIView):
    """
    API-представление для получения случайной заметки.

    Возвращает случайно выбранную актуальную заметку, соответствующую следующим условиям:
    - Срок действия заметки не истёк (поле `dead_line` больше текущего времени).
    - Для анонимных пользователей возвращаются только те заметки, которые не требуют авторизации.
    - Предусмотрена возможность выбора: возвращать только заметки или также допускаются комментарии — 
      через параметр запроса `is-comment`.

    Параметры запроса:
        is-comment: str ("1", "true")
            - Если указан, в результат могут попасть и комментарии, прошедшие фильтрацию.
            - Если не указан, будут возвращены только основные заметки.
    """

    def get(self, request, *args, **kwargs):
        """
        Обрабатывает GET-запрос и возвращает случайную заметку, соответствующую критериям.

        :param request: Объект запроса от DRF
        :return: Response с данными найденной заметки или сообщением об отсутствии подходящих записей.
        """
        now = timezone.now()
        user = request.user

        # Формируем queryset в зависимости от статуса авторизации пользователя
        if user.is_authenticated:
            queryset = Note.objects.filter(dead_line__gt=now)
        else:
            queryset = Note.objects.filter(dead_line__gt=now, only_authorized=False)

        # Если параметр is-comment не разрешён, исключаем комментарии из выборки
        if not self._is_comment_allowed(request):
            queryset = queryset.filter(to_comment=None)

        # Получаем случайную запись
        random_note = queryset.order_by('?').first()

        if not random_note:
            return Response(
                {"detail": "Не найдено ни одной заметки, соответствующей заданным критериям."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = NoteSerializer(random_note)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _is_comment_allowed(self, request):
        """
        Проверяет, разрешено ли включать комментарии в результаты выборки.

        :param request: Объект запроса от DRF
        :return: bool — True, если комментарии разрешены
        """
        is_comment = request.query_params.get("is-comment", "").strip().lower()
        return is_comment in ['1', 'true']
        
# Работа с заметками
class NoteAPI(ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        if user and user.is_authenticated:
            return Note.objects.filter(user=user, dead_line__gt=now, is_burned=False)
        else:
            return Note.objects.filter(dead_line__gt=now, only_authorized=False, is_burned=False)

    def get_object(self):
        user = self.request.user
        note_id = self.kwargs['pk']
        note = get_object_or_404(Note.objects.all(), note_id=note_id, is_burned=False)
        
        # Проверка: актуальность заметки
        if note.dead_line <= timezone.now():
            raise exceptions.NotFound("Note has expired.")

        # Проверка доступа к конкретной заметке
        if note.only_authorized:
            if not (user and user.is_authenticated):
                raise exceptions.PermissionDenied("This note is for authorized users only.")
            
        if note.burn_after_read == True:
            note.is_burned = True
        
        note.save(update_fields=['is_burned'])
        
        return note

class CommentList(APIView):
    pagination_class = CommentPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        """
        Возвращает список комментариев к заметке с возможностью:
        - Получить только количество (`count-comments=1`)
        - Пагинацию
        """
        note_id = kwargs.get('pk')
        
        # 1. Получение заметки или 404
        note = get_object_or_404(Note.objects.all(), note_id=note_id)

        # 2. Определение queryset в зависимости от авторизации пользователя
        now = timezone.now()
        user = request.user

        if user.is_authenticated:
            queryset = note.comments.filter(dead_line__gt=now)
        else:
            queryset = note.comments.filter(
                dead_line__gt=now,
                only_authorized=False
            )

        # 3. Обработка параметра count-comments
        count_only = self._is_count_only_requested(request)
        if count_only:
            return Response({'count': queryset.count()}, status=status.HTTP_200_OK)

        # 4. Пагинация и сериализация
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NoteSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)

    def _is_count_only_requested(self, request):
        """Проверяет, нужно ли вернуть только количество комментариев."""
        value = request.query_params.get('count-comments', '').strip().lower()
        return value in ['1', 'true']

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