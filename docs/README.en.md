# N.D.S.S – Note Distribution and Storage Service

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌍 Russian version

See [`README.md`](README.md)

**Version:** 0.9.5
**Architecture:** Microservice-based
**Purpose:** A service for storing and distributing notes
**Note Format:** Text-based, with public access support
**Deployment:** Kubernetes, Helm, KEDA

---

## 📌 Description

**N.D.S.S** (Note Distribution and Storage Service) is a distributed, horizontally scalable system for storing, distributing, and searching text notes. It is a self-hosted alternative to services like Pastebin, designed with resilience, scalability, and flexibility in mind, suitable for high-load environments.

---

## 🧩 Key Components

### 🧠 Backend

* Built with **Django REST Framework**
* Uses a database router to separate business logic
* Caches:

  * Individual notes
  * Search query results
* Integrates with an external ID generation service
* Asynchronous tasks handled by **Celery** (deletion, update, indexing)

### 💾 Storage

* **PostgreSQL**:

  * Zalando Operator
  * Master–standby replication
  * Scaled with KEDA
* **Redis**:

  * Bitnami chart
  * Master–replica topology
  * Used as both cache and task broker
* **MinIO**:

  * Object storage for note content
* **MeiliSearch**:

  * Full-text search for public notes

### 📊 Monitoring and Logging

* **Prometheus + Grafana** — metrics collection and dashboards
* **Grafana Loki** — centralized logging
* **KEDA** — autoscaling

---

## 🧪 Testing

* Unit tests for DRF APIs
* Service-level testing scripts for:

  * Redis, PostgreSQL, MinIO, MeiliSearch

---

## ⚙️ Deployment

### 🔧 Requirements

* Kubernetes cluster
* Helm 3
* `kubectl` configured with proper context

### 📦 Configuration

Before running the application, you need to create a `.env` file with the required environment variables.
An example file can be found in `.env.template`.

### 📦 Build the backend container

```bash
cd app
docker build -f web.dockerfile -t drf-app:latest .
```

### 🚀 Deploy (via `deploy.sh`)

```bash
chmod +x deploy.sh
./deploy.sh
```

### 🔐 Secrets

All sensitive data is stored in Kubernetes secrets:
- `minio-secret` - MinIO credentials
- `redis-secret` - Redis password
- `meilisearch-secret` - Meilisearch API key
- `postgres-app-secret` - PostgreSQL credentials for the application

If needed, secrets can be updated in the corresponding files:
- `app/minio-secret.yaml`
- `app/redis-secret.yaml`
- `app/secret.yaml`
- `app/postgres-app-secret.yaml`

---

## 🪪 License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

---