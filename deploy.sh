#!/bin/bash
#set -e  # Прервать выполнение при ошибке

# Завершать все background-процессы при выходе из скрипта
#trap 'echo "🧹 Завершаем background-процессы..."; kill $(jobs -p)' EXIT

echo "========================= 🧾 Проверка и создание namespace ========================="

# Проверка и создание namespace для monitoring
kubectl get namespace monitoring > /dev/null 2>&1 || kubectl create namespace monitoring

# Проверка и создание namespace для ingress-nginx
kubectl get namespace ingress-nginx > /dev/null 2>&1 || kubectl create namespace ingress-nginx

# Проверка и создание namespace для meili-system
kubectl get namespace meili-system > /dev/null 2>&1 || kubectl create namespace meili-system

# Проверка и создание namespace для minio
kubectl get namespace minio > /dev/null 2>&1 || kubectl create namespace minio

# Проверка и создание namespace для redis
kubectl get namespace redis > /dev/null 2>&1 || kubectl create namespace redis

# Проверка и создание namespace для postgres-operator
kubectl get namespace postgres-operator > /dev/null 2>&1 || kubectl create namespace postgres-operator

# Проверка и создание namespace для loki
kubectl get namespace loki > /dev/null 2>&1 || kubectl create namespace loki

echo "========================= 🔧 Установка Helm чартов ========================="

# Установка kube-prometheus-stack
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values Promiteus/KPS_values.yaml

# Установка KEDA
helm upgrade --install keda kedacore/keda \
  --namespace monitoring \
  --create-namespace

# Установка ingress-nginx
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values NIC/NIC_values.yaml

echo "========================= 🔐 Установка Meilisearch ========================="

kubectl apply -f meilisearch/secret.yaml
helm upgrade --install meilisearch meilisearch/meilisearch \
  -n meili-system --create-namespace \
  -f meilisearch/meili_values.yaml
kubectl apply -f meilisearch/ServiceMonitor.yaml

echo "========================= 🗄️ Установка MinIO ========================="

kubectl apply -f MiniO/namespace.yaml
kubectl apply -f app/minio-secret.yaml
kubectl apply -f MiniO/minio_conf.yaml

echo "========================= 📦 Установка Loki ========================="

helm upgrade --install loki grafana/loki-stack \
  --namespace loki \
  --values loki/loki-values.yaml \
  --create-namespace

echo "========================= 🧠 Установка Redis ========================="

helm upgrade --install my-redis oci://registry-1.docker.io/bitnamicharts/redis \
  -f my_redis/redis-values.yaml \
  --namespace redis \
  --create-namespace

kubectl apply -f app/redis-secret.yaml

# Копирование секретов в default namespace
echo "========================= 📋 Копирование секретов в default namespace ========================="
kubectl get secret redis-secret -n redis -o yaml | sed 's/namespace: redis/namespace: default/' | kubectl apply -f -
kubectl get secret minio-secret -n minio -o yaml | sed 's/namespace: minio/namespace: default/' | kubectl apply -f -
kubectl get secret meilisearch-secret -n meili-system -o yaml | sed 's/namespace: meili-system/namespace: default/' | kubectl apply -f -
# Для postgresql-secret имя может отличаться, проверим и скопируем его
kubectl get secret root.postgresql-cluster.credentials.postgresql.acid.zalan.do -n postgres-operator -o yaml | sed 's/namespace: postgres-operator/namespace: default/' | kubectl apply -f -

echo "========================= 🐘 Установка PostgreSQL-оператора ========================="

helm upgrade --install postgres-operator postgres-operator-charts/postgres-operator \
  --namespace postgres-operator \
  --create-namespace

kubectl apply -f app/postgres-app-secret.yaml
kubectl apply -f postgreSQL/cluster-conf.yaml

echo "========================= 🌐 Настройка Ingress ========================="

kubectl apply -f NIC/ingress_drf.yaml

echo "========================= Развёртывание центрального генератора ========================="

docker build -f centralized_id_generator/storage/.dockerfile -t redis-cleaner:latest centralized_id_generator/storage
kubectl apply -f centralized_id_generator/storage/cleanup-cronjob.yaml

docker build -f centralized_id_generator/generator/.dockerfile -t key-generator:latest centralized_id_generator/generator
kubectl apply -f centralized_id_generator/generator/key_generator_cronjob.yaml

echo "========================= 🚀 Развёртывание Приложения ========================="

docker build -f app/sidecar/.dockerfile -t flask-l2-cache:latest app/sidecar
docker build -f app/web.dockerfile -t drf-app:latest app/

kubectl apply -f app/secret.yaml
kubectl apply -f app/app.yaml
kubectl apply -f app/ServiceMonitor.yaml
kubectl apply -f celery/celery-worker-deployment.yaml
kubectl apply -f celery/KEDA_Celery.yaml

echo "========================= 🚪 Port-forwarding сервисов ========================="

kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 5000:80 & \
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80 & \
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090 & \
kubectl port-forward -n meili-system svc/meilisearch 7700:7700 & \
kubectl port-forward -n minio svc/minio 9001:9001 & \
kubectl port-forward -n redis svc/my-redis-master 6379:6379 & \
kubectl port-forward -n postgres-operator svc/postgresql-cluster-master 5432:5432 &

echo "⏳ Подождём 5 секунд для стабилизации портов..."
sleep 5

echo "========================= ⚙️ Активация экспериментальных фич Meilisearch ========================="

curl -s \
  -X PATCH 'http://localhost:7700/experimental-features/' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "metrics": true
  }'

echo "✅ Метрики Meilisearch включены"
echo "🎉 Развёртывание завершено!"