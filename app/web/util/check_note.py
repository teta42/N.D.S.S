import logging
from django.utils import timezone
from rest_framework import exceptions
from datetime import datetime


logger = logging.getLogger("myapp")


def check_note(dead_line: datetime, only_authorized: bool, note_id: str, user: object) -> bool:
    # Проверка срока действия
    if dead_line <= timezone.now():
        logger.warning(f"Заметка {note_id} просрочена.")
        raise exceptions.NotFound("Note has expired.")

    # Проверка доступа
    if only_authorized and not (user and user.is_authenticated):
        logger.warning(f"Неавторизованный доступ к защищённой заметке {note_id}")
        raise exceptions.PermissionDenied("This note is for authorized users only.")
    
    return True