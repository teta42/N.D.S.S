# N.D.S.S – Note Distribution and Storage Service
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌍 English Version

See [`README.en.md`](README.en.md)

**Версия:** 0.9.5  
**Архитектура:** Микросервисная  
**Назначение:** Сервис хранения и распространения заметок  
**Формат заметок:** Текстовые, с поддержкой публичного доступа  
**Развёртывание:** Kubernetes, Helm, KEDA

---

## 📌 Описание

**N.D.S.S** (Note Distribution and Storage Service) — это распределённый, масштабируемый сервис для хранения, раздачи и поиска текстовых заметок. Он является собственным аналогом Pastebin, спроектированным с учётом надёжности, горизонтального масштабирования и гибкой архитектуры, подходящей для высоких нагрузок.

---

## 🧩 Ключевые компоненты

### 🧠 Backend

- Реализован с использованием **Django REST Framework**
- Использует роутер баз данных для разделения логики
- Кэширует:
  - Отдельные заметки
  - Результаты поисковых запросов
- Интеграция с внешним сервисом генерации ID
- Асинхронные задачи через **Celery** (удаление, обновление, индексация)

### 💾 Хранилища

- **PostgreSQL**: 

  - Zalando Operator
  - master–standby
  - масштабируется через KEDA
- **Redis**:

  - Bitnami
  - master–replica
  - используется как кэш и брокер
- **MinIO**:

  - объектное хранилище контента
- **MeiliSearch**:

  - полнотекстовый поиск публичных заметок

### 📊 Мониторинг и логирование

- **Prometheus + Grafana** — метрики
- **Grafana Loki** — логирование
- **KEDA** — автоскейлинг

---

## 🧪 Тестирование

- Unit-тесты для DRF API
- Тестовые скрипты для проверки сервисов:

  - Redis, PostgreSQL, MinIO, MeiliSearch

---

## ⚙️ Развёртывание

### 🔧 Требования

- Kubernetes-кластер
- Helm 3
- `kubectl` с нужным контекстом

### 📦 Конфигурация

Перед запуском приложения необходимо создать файл `.env` с необходимыми переменными окружения.
Пример файла можно найти в `.env.template`.

### 📦 Сборка backend-контейнера

```bash
cd app
docker build -f web.dockerfile -t drf-app:latest .
````

### 🚀 Развёртывание (через `deploy.sh`)

```bash
chmod +x deploy.sh
./deploy.sh
```

### 🔐 Секреты

Все чувствительные данные хранятся в Kubernetes секретах:
- `minio-secret` - учетные данные MinIO
- `redis-secret` - пароль Redis
- `meilisearch-secret` - API ключ Meilisearch
- `postgres-app-secret` - учетные данные PostgreSQL для приложения

При необходимости, секреты можно обновить в соответствующих файлах:
- `app/minio-secret.yaml`
- `app/redis-secret.yaml`
- `app/secret.yaml`
- `app/postgres-app-secret.yaml`

---

## 🪪 Лицензия

Проект распространяется под лицензией **MIT**. Подробнее см. файл [`LICENSE`](LICENSE).

---