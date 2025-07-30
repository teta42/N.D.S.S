import requests
import logging

logger = logging.getLogger("myapp")

FLASK_SIDECAR_URL = "http://localhost:8500/get-key"

def get_key_from_sidecar() -> str | None:
    """Запрашивает ключ у Flask-sidecar. Возвращает строку или None при ошибке."""
    try:
        response = requests.get(FLASK_SIDECAR_URL, timeout=2)
        response.raise_for_status()
        data = response.json()
        key = data.get("key")
        if key:
            logger.info(f"✅ Ключ успешно получен от sidecar: {key}")
            return key
        else:
            logger.warning("⚠️ Ответ от sidecar не содержит ключа.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка при запросе к sidecar: {e}")
        return None
