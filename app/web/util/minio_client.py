import boto3
import logging
from django.conf import settings
from functools import lru_cache
from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError

# Получаем логгер Django
logger = logging.getLogger("myapp")

@lru_cache(maxsize=1)
def get_minio_client():
    """
    Создаёт и возвращает клиент MinIO (совместим с Amazon S3), используя настройки Django.
    Все настройки берутся из settings.py.
    """
    try:
        logger.debug("Инициализация MinIO клиента...")

        session = boto3.session.Session()
        client = session.client(
            service_name="s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            verify=settings.AWS_S3_VERIFY,
            config=boto3.session.Config(
                s3={"addressing_style": settings.AWS_S3_ADDRESSING_STYLE}
            )
        )

        logger.info("MinIO клиент успешно создан.")
        return client

    except (BotoCoreError, NoCredentialsError, ClientError) as e:
        logger.exception("Ошибка при создании MinIO клиента: %s", str(e))
        raise
