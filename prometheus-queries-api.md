# 📊 Queries Prometheus para Entersys API Dashboard

## 🔧 Métricas del Contenedor (cAdvisor)

### 1. CPU Usage
```promql
rate(container_cpu_usage_seconds_total{name="entersys-content-api"}[5m]) * 100
```

### 2. Memory Usage
```promql
container_memory_usage_bytes{name="entersys-content-api"} / container_spec_memory_limit_bytes{name="entersys-content-api"} * 100
```

### 3. Memory Usage (MB)
```promql
container_memory_usage_bytes{name="entersys-content-api"} / 1024 / 1024
```

### 4. Container Status
```promql
container_last_seen{name="entersys-content-api"}
```

## 🌐 Health Check Metrics (Blackbox)

### 5. API Health Status
```promql
probe_success{instance="https://api.dev.entersys.mx/api/v1/health"}
```

### 6. API Response Time
```promql
probe_duration_seconds{instance="https://api.dev.entersys.mx/api/v1/health"}
```

### 7. HTTP Status Code
```promql
probe_http_status_code{instance="https://api.dev.entersys.mx/api/v1/health"}
```

## 📝 Logs Monitoring (si Loki está disponible)

### 8. Error Count
```logql
count_over_time({container_name="entersys-content-api"} |= "ERROR" [5m])
```

### 9. Smartsheet Operations
```logql
count_over_time({container_name="entersys-content-api"} |= "smartsheet" [5m])
```

### 10. API Request Count
```logql
count_over_time({container_name="entersys-content-api"} |= "GET /api" [5m])
```

## 📈 Alternative Docker Metrics

### 11. Container Up/Down Status
```promql
up{job="cadvisor", container_label_com_docker_compose_service="api"}
```

### 12. Network I/O
```promql
rate(container_network_receive_bytes_total{name="entersys-content-api"}[5m])
```
```promql
rate(container_network_transmit_bytes_total{name="entersys-content-api"}[5m])
```

## 🚀 Para agregar al Dashboard:

1. **Panel Stat**: Status UP/DOWN
   - Query: `probe_success{instance="https://api.dev.entersys.mx/api/v1/health"}`
   - Thresholds: 0=Red, 1=Green

2. **Panel Graph**: CPU Usage
   - Query: `rate(container_cpu_usage_seconds_total{name="entersys-content-api"}[5m]) * 100`
   - Unit: Percent

3. **Panel Graph**: Memory Usage
   - Query: `container_memory_usage_bytes{name="entersys-content-api"} / 1024 / 1024`
   - Unit: MB

4. **Panel Graph**: Response Time
   - Query: `probe_duration_seconds{instance="https://api.dev.entersys.mx/api/v1/health"}`
   - Unit: Seconds