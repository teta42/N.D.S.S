#!/bin/bash
#set -e  # Прервать выполнение при ошибке

# Завершать все background-процессы при выходе из скрипта
#trap 'echo "🧹 Завершаем background-процессы..."; kill $(jobs -p)' EXIT

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

# HPA для Redis (по желанию)
# kubectl apply -f my_redis/KEDA_HPA.yaml

echo "========================= 🐘 Установка PostgreSQL-оператора ========================="

helm upgrade --install postgres-operator postgres-operator-charts/postgres-operator \
  --namespace postgres-operator \
  --create-namespace

kubectl apply -f postgreSQL/cluster-conf.yaml
kubectl apply -f postgreSQL/HPA.yaml

echo "========================= 🌐 Настройка Ingress и KEDA ========================="

kubectl apply -f NIC/ingress_drf.yaml
kubectl apply -f Promiteus/KEDA_HPA.yaml

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

echo "========================= 🚪 Port-forwarding сервисов ========================="

kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 5000:80 & \
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80 & \
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090 & \
kubectl port-forward -n meili-system svc/meilisearch 7700:7700 & \
kubectl port-forward -n minio svc/minio 9001:9001 &

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