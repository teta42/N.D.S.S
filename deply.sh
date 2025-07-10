helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values Promiteus/KPS_values.yaml

helm upgrade --install keda kedacore/keda \
  --namespace monitoring \
  --create-namespace

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values NIC/NIC_values.yaml

helm upgrade --install meilisearch meilisearch/meilisearch -n meili-system --create-namespace -f meilisearch/meili_values.yaml
kubectl apply -f meilisearch/ServiceMonitor.yaml

kubectl apply -f MiniO/minio_conf.yaml 


helm upgrade --install loki grafana/loki-stack \
  --namespace loki \
  --values loki/loki-values.yaml --create-namespace

helm upgrade --install my-redis oci://registry-1.docker.io/bitnamicharts/redis -f my_redis/redis-values.yaml --namespace redis --create-namespace
# kubectl apply -f my_redis/KEDA_HPA.yaml

helm upgrade --install postgres-operator postgres-operator-charts/postgres-operator \
  --namespace postgres-operator \
  --create-namespace
kubectl apply -f postgreSQL/cluster-conf.yaml
kubectl apply -f postgreSQL/HPA.yaml


kubectl apply -f NIC/ingress_drf.yaml
kubectl apply -f Promiteus/KEDA_HPA.yaml
kubectl apply -f app/app.yaml

kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 5000:80 & \
# kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80 & \
# kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090 & \
# kubectl port-forward --namespace meili-system svc/meilisearch 7700:7700 & \
# kubectl port-forward -n minio svc/minio 9001:9001 & \
curl \
  -X PATCH 'meilisearch.localdev.me:5000/experimental-features/' \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "metrics": true
  }'