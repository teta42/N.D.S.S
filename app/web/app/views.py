from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.request import Request
from django.utils import timezone
from rest_framework import exceptions
from django.shortcuts import get_object_or_404
from .permissions import IsOwnerOrReadOnly
from util.meilisearch import get_meilisearch_index
from meilisearch.errors import MeilisearchApiError, MeilisearchCommunicationError
import logging
from typing import Any

from django.contrib.auth import login, logout

from .pagination import CommentPagination, SearchNotePagination

from .models import Note
from .serializer import (
    NoteSerializer,
    RegisterSerializer,
    LoginSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)


class SearchNote(APIView):
    """
    Обрабатывает GET-запрос для поиска заметок по ключевому слову.

    Использует Meilisearch для полнотекстового поиска.
    Результаты возвращаются с пагинацией через DRF пагинатор.

    Query-параметры:
    - `q` (str): строка поиска (обязательный параметр)
    - `limit` (int): количество элементов на страницу (опционально)
    - `offset` (int): смещение в списке результатов (опционально)
    """

    pagination_class = SearchNotePagination

    def get(self, request: Request) -> Response:
        """
        Обработка GET-запроса на поиск.

        :param request: объект запроса DRF
        :return: JSON-ответ с результатами поиска и мета-информацией пагинации
        """
        query: str = request.query_params.get("q", "").strip()

        if not query:
            logger.warning("Отсутствует обязательный параметр 'q'")
            return Response(
                {"error": "Missing required query parameter 'q'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        paginator = self.pagination_class()

        try:
            # Получаем значения limit и offset
            limit: int = paginator.get_limit(request)
            offset: int = paginator.get_offset(request)

            if limit is None or offset is None:
                logger.warning(f"Некорректные параметры пагинации: limit={limit}, offset={offset}")
                return Response(
                    {"error": "Invalid pagination parameters"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            index = get_meilisearch_index()

            logger.debug(f"Выполняется поиск: query='{query}', limit={limit}, offset={offset}")

            # Выполняем поиск
            result: dict[str, Any] = index.search(query, {
                "offset": offset,
                "limit": limit
            })

            hits: list[dict[str, Any]] = result.get("hits", [])
            total_hits: int = result.get("estimatedTotalHits", 0)

            # Используем DRF-пагинацию вручную
            page = paginator.paginate_queryset(hits, request, view=self)

            if page is None:
                logger.warning("Paginator вернул None — вероятно, ошибка в параметрах")
                return Response(
                    {"error": "Pagination failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Встраиваем общее количество найденных записей
            response = paginator.get_paginated_response(page)
            response.data["total_hits"] = total_hits

            logger.info(f"Поиск выполнен успешно: найдено {total_hits} записей")
            return response

        except MeilisearchApiError as e:
            logger.exception("Ошибка Meilisearch API при поиске")
            return Response(
                {"error": f"Meilisearch API error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except MeilisearchCommunicationError as e:
            logger.exception("Ошибка связи с Meilisearch")
            return Response(
                {"error": "Cannot connect to Meilisearch"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.exception("Непредвиденная ошибка при поиске")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    def get(self, request: Request, *args, **kwargs):
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

    def get(self, request: Request, *args, **kwargs):
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
    def post(self, request: Request):
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
    def post(self, request: Request):
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

    def get(self, request: Request):
        logout(request)
        return Response({"message": "Выход выполнен успешно"}, status=status.HTTP_200_OK)


class UpdateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request):
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

    def patch(self, request: Request):
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

    def delete(self, request: Request):
        user = request.user
        user.delete()
        return Response({"message": "Аккаунт удален"}, status=status.HTTP_204_NO_CONTENT)