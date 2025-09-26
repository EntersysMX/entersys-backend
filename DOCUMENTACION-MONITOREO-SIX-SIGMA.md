# 📊 GUÍA COMPLETA DE MONITOREO SIX SIGMA - ENTERSYS

## 🎯 **OBJETIVO: ALCANZAR EL MÉTODO 3 SEGUNDOS**

Esta documentación estandariza el proceso de agregar nuevas aplicaciones al sistema de monitoreo de Entersys para medir y alcanzar los estándares de Six Sigma (99.99966% de disponibilidad).

---

## 🏗️ **ARQUITECTURA DE MONITOREO**

### **Stack Tecnológico:**
- **Prometheus**: Recolección de métricas
- **Grafana**: Visualización y dashboards
- **Blackbox Exporter**: Monitoreo de endpoints HTTP/HTTPS/TCP
- **cAdvisor**: Métricas de contenedores Docker
- **Node Exporter**: Métricas del sistema operativo
- **Loki**: Agregación y consulta de logs (opcional)
- **Alertmanager**: Gestión de alertas

### **Dashboard Principal:**
```
https://monitoring.entersys.mx/d/entersys-3s/f09f8eaf-entersys-metodo-3-segundos
```

---

## 📋 **PARTE 1: AGREGAR APLICACIONES CON CONTENEDOR DOCKER**

### **Paso 1: Preparar la Aplicación**

#### **1.1 Health Check Endpoint**
Toda aplicación debe exponer un endpoint de salud:

```javascript
// Ejemplo Node.js/Express
app.get('/api/v1/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      database: { status: 'healthy' },
      external_api: { status: 'ready' }
    }
  });
});
```

```python
# Ejemplo Python/FastAPI
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": {"status": "healthy"},
            "external_api": {"status": "ready"}
        }
    }
```

#### **1.2 Dockerfile con Labels**
Agregar labels de monitoreo al Dockerfile:

```dockerfile
FROM node:18-alpine

# Labels para monitoreo
LABEL monitoring.prometheus.scrape="true"
LABEL monitoring.prometheus.port="3000"
LABEL monitoring.prometheus.path="/metrics"
LABEL monitoring.health.endpoint="/api/v1/health"
LABEL monitoring.service.name="mi-aplicacion"
LABEL monitoring.service.version="1.0.0"

COPY . /app
WORKDIR /app
RUN npm install
EXPOSE 3000
CMD ["npm", "start"]
```

### **Paso 2: Configurar Docker Compose**

```yaml
# docker-compose.yml
version: '3.8'

services:
  mi-aplicacion:
    build: .
    container_name: mi-aplicacion-api
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_CONNECTION_STRING=${DB_CONNECTION_STRING}
    labels:
      # Traefik routing
      - "traefik.enable=true"
      - "traefik.http.routers.mi-app.rule=Host(`mi-app.entersys.mx`)"
      - "traefik.http.routers.mi-app.tls.certresolver=letsencrypt"
      # Monitoring labels
      - "monitoring.service=mi-aplicacion"
      - "monitoring.health=/api/v1/health"
    networks:
      - entersys-network
    restart: unless-stopped

networks:
  entersys-network:
    external: true
```

### **Paso 3: Actualizar Prometheus**

#### **3.1 Conectarse al Servidor**
```bash
gcloud compute ssh dev-server --zone=us-central1-c
```

#### **3.2 Backup y Editar Configuración**
```bash
# Crear backup
docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus-backup.yml

# Copiar configuración actual
docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus.yml
```

#### **3.3 Agregar Job de Monitoreo**
Editar `/tmp/prometheus.yml` y agregar:

```yaml
# NUEVA APLICACIÓN: MI-APLICACION
  - job_name: 'mi-aplicacion'
    static_configs:
      - targets: ['mi-aplicacion-api:3000']
    metrics_path: '/metrics'  # Si expone métricas Prometheus
    scrape_interval: 15s

  # Health Check via Blackbox
  - job_name: 'blackbox-mi-aplicacion'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://mi-app.entersys.mx/api/v1/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: entersys-blackbox-exporter:9115
```

#### **3.4 Aplicar Configuración**
```bash
# Copiar configuración actualizada
docker cp /tmp/prometheus.yml entersys-prometheus:/etc/prometheus/prometheus.yml

# Reiniciar Prometheus
docker restart entersys-prometheus

# Verificar logs
docker logs entersys-prometheus --tail 20
```

### **Paso 4: Crear Panel en Grafana**

#### **4.1 Configuración del Panel**
```json
{
  "datasource": {
    "type": "prometheus",
    "uid": "PBFA97CFB590B2093"
  },
  "fieldConfig": {
    "defaults": {
      "color": {"mode": "thresholds"},
      "mappings": [
        {"options": {"0": {"color": "red", "text": "DOWN"}}, "type": "value"},
        {"options": {"1": {"color": "green", "text": "UP"}}, "type": "value"}
      ],
      "thresholds": {
        "steps": [
          {"color": "red", "value": null},
          {"color": "green", "value": 1}
        ]
      }
    }
  },
  "targets": [
    {
      "expr": "probe_success{instance=\"https://mi-app.entersys.mx/api/v1/health\"}",
      "legendFormat": "🔗 Mi Aplicación"
    }
  ],
  "title": "🔗 MI APLICACIÓN",
  "type": "stat"
}
```

---

## 🖥️ **PARTE 2: AGREGAR APLICACIONES SIN CONTENEDOR**

### **Paso 1: Instalar Node Exporter (si no existe)**

#### **En el servidor de la aplicación:**
```bash
# Descargar Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz

# Extraer y configurar
tar xvfz node_exporter-*.tar.gz
sudo mv node_exporter-*/node_exporter /usr/local/bin/
sudo useradd -rs /bin/false node_exporter

# Crear servicio systemd
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter --web.listen-address=:9100

[Install]
WantedBy=multi-user.target
EOF

# Habilitar y iniciar
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
```

### **Paso 2: Configurar Application Metrics**

#### **2.1 Para aplicaciones Node.js**
```javascript
// Instalar: npm install prom-client
const client = require('prom-client');

// Crear métricas personalizadas
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10]
});

const httpRequestTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status']
});

// Middleware para métricas
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestDuration.labels(req.method, req.route?.path || req.path, res.statusCode).observe(duration);
    httpRequestTotal.labels(req.method, req.route?.path || req.path, res.statusCode).inc();
  });

  next();
});

// Endpoint de métricas
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});
```

#### **2.2 Para aplicaciones Python**
```python
# Instalar: pip install prometheus-client
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

# Métricas personalizadas
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Middleware Flask
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    request_duration = time.time() - request.start_time
    REQUEST_DURATION.labels(request.method, request.endpoint or 'unknown').observe(request_duration)
    REQUEST_COUNT.labels(request.method, request.endpoint or 'unknown', response.status_code).inc()
    return response

# Endpoint de métricas
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
```

### **Paso 3: Configurar Prometheus para App Externa**

```yaml
# Agregar a prometheus.yml
  - job_name: 'mi-app-externa'
    static_configs:
      - targets: ['IP_SERVIDOR:PUERTO']  # Ej: 192.168.1.100:3000
    metrics_path: '/metrics'
    scrape_interval: 15s

  # Node Exporter del servidor
  - job_name: 'node-mi-servidor'
    static_configs:
      - targets: ['IP_SERVIDOR:9100']
    scrape_interval: 15s

  # Health check externo
  - job_name: 'blackbox-mi-app-externa'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://IP_SERVIDOR:PUERTO/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: entersys-blackbox-exporter:9115
```

---

## 📝 **PARTE 3: CONFIGURACIÓN HOMOGÉNEA DE LOGS**

### **Estándar de Logs para Six Sigma**

#### **3.1 Formato JSON Estructurado**
Todos los servicios deben usar este formato:

```json
{
  "timestamp": "2025-09-25T10:30:45.123Z",
  "level": "INFO|WARN|ERROR|DEBUG",
  "service": "nombre-servicio",
  "version": "1.0.0",
  "request_id": "uuid-del-request",
  "user_id": "identificador-usuario",
  "action": "descripcion-accion",
  "duration_ms": 250,
  "status": "success|error|pending",
  "message": "Mensaje legible",
  "metadata": {
    "ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "endpoint": "/api/v1/endpoint",
    "method": "GET|POST|PUT|DELETE"
  },
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message",
    "stack": "Stack trace..."
  }
}
```

#### **3.2 Implementación por Tecnología**

**Node.js con Winston:**
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'mi-aplicacion',
    version: process.env.APP_VERSION || '1.0.0'
  },
  transports: [
    new winston.transports.File({
      filename: '/app/logs/error.log',
      level: 'error',
      maxsize: 10485760, // 10MB
      maxFiles: 10
    }),
    new winston.transports.File({
      filename: '/app/logs/app.log',
      maxsize: 10485760,
      maxFiles: 10
    }),
    new winston.transports.Console()
  ]
});

// Middleware de logging
app.use((req, res, next) => {
  const start = Date.now();
  const requestId = require('uuid').v4();
  req.requestId = requestId;

  res.on('finish', () => {
    logger.info({
      request_id: requestId,
      action: `${req.method} ${req.path}`,
      duration_ms: Date.now() - start,
      status: res.statusCode < 400 ? 'success' : 'error',
      metadata: {
        ip: req.ip,
        user_agent: req.get('User-Agent'),
        endpoint: req.path,
        method: req.method,
        status_code: res.statusCode
      }
    });
  });

  next();
});
```

**Python con Structlog:**
```python
import structlog
import logging
from pythonjsonlogger import jsonlogger

# Configurar logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.LoggerAdapter,
    logger_factory=structlog.stdlib.LoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)

# Configurar handler
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Usar en aplicación
log = structlog.get_logger()

@app.before_request
def before_request():
    request.start_time = time.time()
    request.request_id = str(uuid.uuid4())

@app.after_request
def after_request(response):
    duration_ms = (time.time() - request.start_time) * 1000

    log.info(
        "Request completed",
        service="mi-aplicacion",
        version=os.getenv('APP_VERSION', '1.0.0'),
        request_id=request.request_id,
        action=f"{request.method} {request.path}",
        duration_ms=round(duration_ms, 2),
        status="success" if response.status_code < 400 else "error",
        metadata={
            "ip": request.remote_addr,
            "user_agent": request.user_agent.string,
            "endpoint": request.path,
            "method": request.method,
            "status_code": response.status_code
        }
    )
    return response
```

#### **3.3 Rotación de Logs**

**Para aplicaciones Docker:**
```yaml
# docker-compose.yml
services:
  mi-aplicacion:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "10"
    volumes:
      - ./logs:/app/logs
```

**Para aplicaciones del sistema:**
```bash
# /etc/logrotate.d/mi-aplicacion
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 0644 app app
    postrotate
        systemctl reload mi-aplicacion || true
    endscript
}
```

---

## 📊 **PARTE 4: MÉTRICAS SIX SIGMA ESTANDARIZADAS**

### **4.1 KPIs Críticos a Monitorear**

#### **Disponibilidad (Uptime)**
```promql
# Porcentaje de disponibilidad en 24h
(
  sum(up{service="mi-aplicacion"}[24h]) /
  count(up{service="mi-aplicacion"}[24h])
) * 100

# Meta Six Sigma: >= 99.99966%
```

#### **Tiempo de Respuesta**
```promql
# Percentil 95 del tiempo de respuesta
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{service="mi-aplicacion"}[5m])
)

# Meta Six Sigma: <= 3 segundos
```

#### **Tasa de Errores**
```promql
# Porcentaje de errores HTTP
(
  sum(rate(http_requests_total{service="mi-aplicacion",status=~"5.."}[5m])) /
  sum(rate(http_requests_total{service="mi-aplicacion"}[5m]))
) * 100

# Meta Six Sigma: <= 0.00034%
```

#### **Throughput**
```promql
# Requests por segundo
sum(rate(http_requests_total{service="mi-aplicacion"}[1m]))
```

### **4.2 Alertas Six Sigma**

#### **Crear archivo de alertas:**
```yaml
# /etc/prometheus/alerts/six-sigma-alerts.yml
groups:
- name: six-sigma-sla
  rules:

  # Disponibilidad crítica
  - alert: ServiceDownCritical
    expr: up{service="mi-aplicacion"} == 0
    for: 10s
    labels:
      severity: critical
      sla: six-sigma
    annotations:
      summary: "Servicio {{ $labels.service }} está DOWN"
      description: "El servicio ha estado DOWN por más de 10 segundos. SLA Six Sigma comprometido."

  # Tiempo de respuesta excesivo
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="mi-aplicacion"}[5m])) > 3
    for: 2m
    labels:
      severity: warning
      sla: six-sigma
    annotations:
      summary: "Tiempo de respuesta alto en {{ $labels.service }}"
      description: "P95 de tiempo de respuesta es {{ $value }}s, excede el límite de 3s Six Sigma."

  # Tasa de error alta
  - alert: HighErrorRate
    expr: (sum(rate(http_requests_total{service="mi-aplicacion",status=~"5.."}[5m])) / sum(rate(http_requests_total{service="mi-aplicacion"}[5m]))) * 100 > 0.1
    for: 1m
    labels:
      severity: critical
      sla: six-sigma
    annotations:
      summary: "Alta tasa de errores en {{ $labels.service }}"
      description: "Tasa de errores es {{ $value }}%, excede el límite Six Sigma de 0.00034%."
```

---

## 🎯 **PARTE 5: DASHBOARD TEMPLATE SIX SIGMA**

### **5.1 Panel de Estado Principal**
```json
{
  "title": "🚦 ESTADO GENERAL - SIX SIGMA",
  "type": "stat",
  "targets": [
    {
      "expr": "avg(up{job=~\".*\"})",
      "legendFormat": "🌐 DISPONIBILIDAD GENERAL"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "min": 0.9999,
      "max": 1,
      "thresholds": {
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 0.999},
          {"color": "green", "value": 0.99999}
        ]
      },
      "unit": "percentunit"
    }
  }
}
```

### **5.2 Tabla de SLA por Servicio**
```json
{
  "title": "📊 SLA STATUS - SIX SIGMA COMPLIANCE",
  "type": "table",
  "targets": [
    {
      "expr": "avg_over_time(up[24h])",
      "format": "table",
      "instant": true
    }
  ],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "renameByName": {
          "Value": "Disponibilidad 24h",
          "service": "Servicio"
        }
      }
    }
  ],
  "fieldConfig": {
    "overrides": [
      {
        "matcher": {"id": "byName", "options": "Disponibilidad 24h"},
        "properties": [
          {
            "id": "custom.cellOptions",
            "value": {"type": "color-background"}
          },
          {
            "id": "thresholds",
            "value": {
              "steps": [
                {"color": "red", "value": null},
                {"color": "yellow", "value": 0.999},
                {"color": "green", "value": 0.99999}
              ]
            }
          }
        ]
      }
    ]
  }
}
```

---

## 🔧 **PARTE 6: SCRIPT DE AUTOMATIZACIÓN**

### **6.1 Script para Agregar Nuevo Servicio**
```bash
#!/bin/bash
# add-monitoring.sh

SERVICE_NAME=$1
SERVICE_URL=$2
CONTAINER_NAME=$3

if [ $# -lt 2 ]; then
    echo "Uso: $0 <service-name> <service-url> [container-name]"
    echo "Ejemplo: $0 mi-app https://mi-app.entersys.mx mi-app-container"
    exit 1
fi

echo "🔄 Agregando $SERVICE_NAME al monitoreo Six Sigma..."

# 1. Backup Prometheus config
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus-backup-$(date +%Y%m%d).yml"

# 2. Agregar configuración
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus.yml"

# 3. Agregar endpoint al blackbox
gcloud compute ssh dev-server --zone=us-central1-c --command="sed -i '/# Production Websites/a\        - $SERVICE_URL/health' /tmp/prometheus.yml"

# 4. Si es contenedor, agregar métricas de contenedor
if [ ! -z "$CONTAINER_NAME" ]; then
    echo "📦 Configurando monitoreo de contenedor: $CONTAINER_NAME"
    # Agregar job específico si el contenedor expone métricas
fi

# 5. Aplicar configuración
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp /tmp/prometheus.yml entersys-prometheus:/etc/prometheus/prometheus.yml && docker restart entersys-prometheus"

echo "✅ $SERVICE_NAME agregado exitosamente al monitoreo"
echo "🎯 Dashboard: https://monitoring.entersys.mx/d/entersys-3s/"
echo "📊 Prometheus: https://monitoring.entersys.mx:9090"
```

### **6.2 Script de Validación SLA**
```bash
#!/bin/bash
# check-six-sigma-compliance.sh

echo "🎯 VERIFICACIÓN SIX SIGMA COMPLIANCE - ENTERSYS"
echo "================================================"

# Obtener métricas de disponibilidad
PROMETHEUS_URL="https://monitoring.entersys.mx:9090"

# Verificar disponibilidad de cada servicio
services=$(curl -s "$PROMETHEUS_URL/api/v1/label/service/values" | jq -r '.data[]')

for service in $services; do
    # Calcular disponibilidad 24h
    uptime=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=avg_over_time(up{service=\"$service\"}[24h])" | jq -r '.data.result[0].value[1]')

    if (( $(echo "$uptime >= 0.9999966" | bc -l) )); then
        echo "✅ $service: $(printf "%.6f" $uptime) - SIX SIGMA COMPLIANT"
    else
        echo "❌ $service: $(printf "%.6f" $uptime) - SLA BREACH"
    fi
done

echo "================================================"
echo "🎯 Meta Six Sigma: >= 99.99966% disponibilidad"
```

---

## 📋 **CHECKLIST DE IMPLEMENTACIÓN**

### **Para Nuevas Aplicaciones:**
- [ ] ✅ Health endpoint implementado (`/api/v1/health`)
- [ ] ✅ Métricas Prometheus expuestas (`/metrics`)
- [ ] ✅ Logs estructurados en formato JSON
- [ ] ✅ Rotación de logs configurada (10MB, 10 archivos)
- [ ] ✅ Labels Docker para monitoreo
- [ ] ✅ Configuración agregada a Prometheus
- [ ] ✅ Panel creado en Grafana dashboard
- [ ] ✅ Alertas Six Sigma configuradas
- [ ] ✅ Validación de métricas funcionando
- [ ] ✅ SLA compliance verificado

### **Métricas Obligatorias:**
- [ ] ✅ Disponibilidad (uptime)
- [ ] ✅ Tiempo de respuesta (response time)
- [ ] ✅ Tasa de errores (error rate)
- [ ] ✅ Throughput (requests/second)
- [ ] ✅ Uso de CPU (si contenedor)
- [ ] ✅ Uso de memoria (si contenedor)
- [ ] ✅ Conexiones de red (si aplicable)

---

## 🎯 **ESTÁNDARES SIX SIGMA - OBJETIVOS**

### **Métricas de Calidad:**
- **Disponibilidad**: >= 99.99966% (3.4 defectos por millón)
- **Tiempo de Respuesta**: <= 3 segundos (P95)
- **Tasa de Errores**: <= 0.00034%
- **MTTR** (Mean Time to Recovery): <= 5 minutos
- **MTBF** (Mean Time Between Failures): >= 1 año

### **Dashboard URL:**
```
https://monitoring.entersys.mx/d/entersys-3s/f09f8eaf-entersys-metodo-3-segundos
```

### **Acceso:**
- **Usuario**: admin
- **Password**: admin123

---

## 📞 **SOPORTE Y TROUBLESHOOTING**

### **Comandos Útiles:**
```bash
# Verificar estado de Prometheus
docker logs entersys-prometheus --tail 20

# Verificar configuración
curl -s https://monitoring.entersys.mx:9090/api/v1/status/config

# Verificar targets activos
curl -s https://monitoring.entersys.mx:9090/api/v1/targets

# Reiniciar stack de monitoreo
docker restart entersys-prometheus entersys-grafana entersys-blackbox-exporter
```

### **Troubleshooting Común:**
1. **Servicio no aparece en dashboard**: Verificar configuración Prometheus y labels
2. **Métricas sin datos**: Confirmar que el endpoint `/metrics` esté accesible
3. **Alertas no funcionan**: Revisar reglas de alertas y Alertmanager
4. **Dashboard no carga**: Verificar permisos y configuración de Grafana

---

**🎯 OBJETIVO: MÉTODO 3 SEGUNDOS - SIX SIGMA COMPLIANCE**

Esta documentación asegura que todas las aplicaciones de Entersys alcancen los estándares de excelencia Six Sigma con 99.99966% de disponibilidad y tiempos de respuesta <= 3 segundos.