import hashlib
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.request import Request
from django.utils import timezone
from rest_framework import exceptions, request as drf_request
from django.shortcuts import get_object_or_404
from .permissions import IsOwnerOrReadOnly
from util.meilisearch import get_meilisearch_index
from meilisearch.errors import MeilisearchApiError, MeilisearchCommunicationError
import logging
from typing import Any
from util.cache import wcache, rcache
from util.norm import normalize_string
from util.check_note import check_note
from django.utils.dateparse import parse_datetime

from django.contrib.auth import login, logout

from .pagination import CommentPagination, SearchNotePagination

from .models import Note
from .serializer import (
    NoteSerializer,
    RegisterSerializer,
    LoginSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger("myapp")

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
        query: str = request.query_params.get("q", "").strip()
        
        if not query:
            logger.warning("Отсутствует обязательный параметр 'q'")
            return Response(
                {"error": "Missing required query parameter 'q'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        paginator = self.pagination_class()

        try:
            limit: int = paginator.get_limit(request)
            offset: int = paginator.get_offset(request)

            if limit is None or offset is None:
                logger.warning(f"Некорректные параметры пагинации: limit={limit}, offset={offset}")
                return Response(
                    {"error": "Invalid pagination parameters"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Формируем ключ кэша
            raw_key = f"{normalize_string(query)}:{limit}:{offset}"
            cache_key = hashlib.md5(raw_key.encode("utf-8")).hexdigest()

            # Пробуем достать результат из кэша
            cached_result = rcache().get(cache_key)
            if cached_result:
                logger.info(f"Кэш найден по ключу: {cache_key}")
                result = json.loads(cached_result)
            else:
                index = get_meilisearch_index()
                logger.debug(f"Выполняется поиск: query='{query}', limit={limit}, offset={offset}")

                result: dict[str, Any] = index.search(query, {
                    "offset": offset,
                    "limit": limit
                })

                # Сохраняем результат в Redis
                wcache().set(cache_key, json.dumps(result), timeout=60*5)
                logger.info(f"Результат закэширован с ключом: {cache_key}")

            hits = result.get("hits", [])
            total_hits = result.get("estimatedTotalHits", 0)

            page = paginator.paginate_queryset(hits, request, view=self)
            if page is None:
                logger.warning("Paginator вернул None — вероятно, ошибка в параметрах")
                return Response(
                    {"error": "Pagination failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            response = paginator.get_paginated_response(page)
            response.data["total_hits"] = total_hits

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
        
class NoteAPI(ModelViewSet):
    """
    API для работы с заметками.
    
    Поддерживает просмотр заметок с учётом срока действия, авторизации и флага burn_after_read.
    Использует кэш Redis для повышения производительности.
    """
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self) -> Any:
        """
        Возвращает набор заметок, доступных текущему пользователю.
        Учитываются: авторизация, срок действия и статус удаления (is_burned).
        """
        try:
            user = self.request.user
            now = timezone.now()

            if user and user.is_authenticated:
                return Note.objects.filter(user=user, dead_line__gt=now, is_burned=False)
            else:
                return Note.objects.filter(dead_line__gt=now, only_authorized=False, is_burned=False)

        except Exception as e:
            logger.exception("Ошибка в get_queryset: %s", str(e))
            raise exceptions.APIException("Ошибка при получении списка заметок")

    def get_object(self) -> Note:
        """
        Получает конкретную заметку с учётом:
        - срока действия (dead_line)
        - доступа (only_authorized)
        - удаления при прочтении (burn_after_read)
        """
        try:
            user = self.request.user
            note_id = self.kwargs.get('pk')

            # Поиск заметки
            note = get_object_or_404(Note.objects.all(), note_id=note_id, is_burned=False)

            check_note(note.dead_line, note.only_authorized, note.note_id, user)

            # Автоматическое сгорание заметки после прочтения
            if note.burn_after_read:
                note.is_burned = True
                note.save(update_fields=['is_burned'])
                logger.info(f"Заметка {note_id} была сожжена после прочтения.")

            return note

        except exceptions.APIException:
            raise  # Уже логировано выше
        except Exception as e:
            logger.exception("Неизвестная ошибка в get_object: %s", str(e))
            raise exceptions.APIException("Ошибка при получении заметки")

    def retrieve(self, request: drf_request.Request, *args: Any, **kwargs: Any) -> Response:
        """
        Получает одну заметку:
        - Сначала пытается взять её из кэша (если нет флага burn_after_read)
        - Если не найдено — извлекает из БД через get_object()
        - Кладёт в кэш на 10 минут, если не требует сгорания после чтения
        """
        try:
            note_id = self.kwargs.get("pk")
            cache_key = f"note:{note_id}"

            # Проверка в кэше
            cached_data = rcache().get(cache_key)
            if cached_data is not None:
                logger.info(f"Заметка {note_id} найдена в кэше.")
                check_note(
                    dead_line=parse_datetime(cached_data["dead_line"]),
                    only_authorized=cached_data["only_authorized"],
                    note_id=note_id,
                    user=request.user
                )
                return Response(cached_data)

            # Если нет в кэше — достаём из БД
            note = self.get_object()
            serializer = self.get_serializer(note)
            data = serializer.data

            # Кэшируем только если не сжигается после прочтения
            if not note.burn_after_read:
                wcache().set(cache_key, data, timeout=600)  # 10 минут
                logger.info(f"Заметка {note_id} закэширована.")

            return Response(data)

        except exceptions.APIException:
            raise
        except Exception as e:
            logger.exception("Неизвестная ошибка в retrieve: %s", str(e))
            raise exceptions.APIException("Ошибка при получении заметки")
    
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