#!/bin/bash
# 🎯 SCRIPT AUTOMÁTICO - AGREGAR SERVICIO A MONITOREO SIX SIGMA
# Autor: Sistema de Monitoreo Entersys
# Versión: 1.0.0

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
SERVICE_NAME=$1
SERVICE_URL=$2
CONTAINER_NAME=$3
SERVICE_PORT=$4
METRICS_PATH=${5:-"/metrics"}
HEALTH_PATH=${6:-"/api/v1/health"}

# Función de ayuda
show_help() {
    echo "🎯 SCRIPT DE MONITOREO SIX SIGMA - ENTERSYS"
    echo "=============================================="
    echo ""
    echo "Uso: $0 <service-name> <service-url> [container-name] [port] [metrics-path] [health-path]"
    echo ""
    echo "Parámetros:"
    echo "  service-name    : Nombre del servicio (ej: mi-app)"
    echo "  service-url     : URL del servicio (ej: https://mi-app.entersys.mx)"
    echo "  container-name  : Nombre del contenedor Docker (opcional)"
    echo "  port           : Puerto del servicio (opcional, default: extraído de URL)"
    echo "  metrics-path   : Path de métricas (opcional, default: /metrics)"
    echo "  health-path    : Path de health check (opcional, default: /api/v1/health)"
    echo ""
    echo "Ejemplos:"
    echo "  # Aplicación con contenedor"
    echo "  $0 smartsheet-api https://api.dev.entersys.mx entersys-content-api 8000"
    echo ""
    echo "  # Aplicación sin contenedor"
    echo "  $0 external-app https://external.entersys.mx"
    echo ""
    echo "  # Aplicación con paths personalizados"
    echo "  $0 custom-app https://custom.entersys.mx custom-container 3000 /custom/metrics /custom/health"
    echo ""
    exit 1
}

# Validar parámetros
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Error: Parámetros insuficientes${NC}"
    show_help
fi

# Función para log con timestamp
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "🎯 =================================="
echo "   MONITOREO SIX SIGMA - ENTERSYS"
echo "   Agregando: $SERVICE_NAME"
echo "   URL: $SERVICE_URL"
echo "=================================="
echo -e "${NC}"

# Validar conectividad con el servidor
log "Validando conectividad con servidor de monitoreo..."
if ! gcloud compute ssh dev-server --zone=us-central1-c --command="echo 'Conexión exitosa'" >/dev/null 2>&1; then
    log_error "No se puede conectar al servidor de monitoreo"
    log_error "Verificar: gcloud auth login && gcloud config set project mi-infraestructura-web"
    exit 1
fi
log_success "Conectividad con servidor validada"

# Crear backup de configuración
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
log "Creando backup de configuración Prometheus..."
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus-backup-$BACKUP_DATE.yml"
log_success "Backup creado: /tmp/prometheus-backup-$BACKUP_DATE.yml"

# Copiar configuración actual
log "Obteniendo configuración actual de Prometheus..."
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp entersys-prometheus:/etc/prometheus/prometheus.yml /tmp/prometheus.yml"

# Validar que el servicio no esté ya configurado
log "Validando que el servicio no esté duplicado..."
if gcloud compute ssh dev-server --zone=us-central1-c --command="grep -q '$SERVICE_URL' /tmp/prometheus.yml"; then
    log_warning "El servicio $SERVICE_NAME ya parece estar configurado"
    echo -n "¿Desea continuar de todos modos? (y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "Operación cancelada por el usuario"
        exit 0
    fi
fi

# Construir configuración basada en parámetros
log "Construyendo configuración de monitoreo..."

# 1. Agregar health check a blackbox exporter
HEALTH_URL="$SERVICE_URL$HEALTH_PATH"
log "Agregando health check: $HEALTH_URL"

gcloud compute ssh dev-server --zone=us-central1-c --command="
# Agregar URL al blackbox monitoring
sed -i '/# Production Websites/a\\        - $HEALTH_URL' /tmp/prometheus.yml
"

# 2. Si hay contenedor, agregar job específico para métricas del contenedor
if [ ! -z "$CONTAINER_NAME" ]; then
    log "Configurando monitoreo de contenedor: $CONTAINER_NAME"

    # Crear job para métricas de aplicación (si expone /metrics)
    if [ "$METRICS_PATH" != "none" ]; then
        log "Agregando job de métricas de aplicación"

        # Detectar puerto si no se proporciona
        if [ -z "$SERVICE_PORT" ]; then
            if [[ "$SERVICE_URL" =~ :([0-9]+) ]]; then
                SERVICE_PORT="${BASH_REMATCH[1]}"
            elif [[ "$SERVICE_URL" =~ ^https ]]; then
                SERVICE_PORT="443"
            else
                SERVICE_PORT="80"
            fi
        fi

        gcloud compute ssh dev-server --zone=us-central1-c --command="
# Agregar job específico para la aplicación
cat >> /tmp/prometheus.yml << 'EOFMETRICS'

  # $SERVICE_NAME Application Metrics
  - job_name: '$SERVICE_NAME-app'
    static_configs:
      - targets: ['$CONTAINER_NAME:$SERVICE_PORT']
    metrics_path: '$METRICS_PATH'
    scrape_interval: 15s
    scrape_timeout: 10s
EOFMETRICS
"
    fi

    log_success "Configuración de contenedor agregada"
fi

# 3. Agregar job para métricas del sistema (si es servidor externo)
if [ -z "$CONTAINER_NAME" ]; then
    log "Detectando configuración para servidor externo..."

    # Extraer host de la URL
    HOST=$(echo "$SERVICE_URL" | sed 's|^https\?://||' | sed 's|/.*||' | sed 's|:.*||')

    log "Host detectado: $HOST"
    log_warning "Para monitoreo completo de servidor externo, asegúrate de que Node Exporter esté instalado en $HOST:9100"

    # Si se especifica puerto y métricas, agregar job
    if [ ! -z "$SERVICE_PORT" ] && [ "$METRICS_PATH" != "none" ]; then
        gcloud compute ssh dev-server --zone=us-central1-c --command="
# Agregar job para aplicación externa
cat >> /tmp/prometheus.yml << 'EOFEXTERNAL'

  # $SERVICE_NAME External Application
  - job_name: '$SERVICE_NAME-external'
    static_configs:
      - targets: ['$HOST:$SERVICE_PORT']
    metrics_path: '$METRICS_PATH'
    scrape_interval: 15s
    scrape_timeout: 10s
EOFEXTERNAL
"
    fi
fi

# Validar configuración YAML
log "Validando sintaxis de configuración YAML..."
if ! gcloud compute ssh dev-server --zone=us-central1-c --command="python3 -c 'import yaml; yaml.safe_load(open(\"/tmp/prometheus.yml\"))'" 2>/dev/null; then
    log_error "Error en sintaxis YAML. Restaurando backup..."
    gcloud compute ssh dev-server --zone=us-central1-c --command="cp /tmp/prometheus-backup-$BACKUP_DATE.yml /tmp/prometheus.yml"
    exit 1
fi
log_success "Sintaxis YAML validada"

# Aplicar configuración
log "Aplicando configuración a Prometheus..."
gcloud compute ssh dev-server --zone=us-central1-c --command="docker cp /tmp/prometheus.yml entersys-prometheus:/etc/prometheus/prometheus.yml"

# Reiniciar Prometheus
log "Reiniciando Prometheus..."
gcloud compute ssh dev-server --zone=us-central1-c --command="docker restart entersys-prometheus"

# Esperar a que Prometheus se reinicie
log "Esperando a que Prometheus se reinicie..."
sleep 10

# Validar que Prometheus esté funcionando
log "Validando que Prometheus esté operativo..."
PROMETHEUS_STATUS=""
for i in {1..30}; do
    if gcloud compute ssh dev-server --zone=us-central1-c --command="curl -s http://localhost:9090/-/healthy" >/dev/null 2>&1; then
        PROMETHEUS_STATUS="healthy"
        break
    fi
    sleep 2
done

if [ "$PROMETHEUS_STATUS" != "healthy" ]; then
    log_error "Prometheus no responde después del reinicio"
    log_error "Restaurando configuración de backup..."
    gcloud compute ssh dev-server --zone=us-central1-c --command="
        cp /tmp/prometheus-backup-$BACKUP_DATE.yml /tmp/prometheus.yml
        docker cp /tmp/prometheus.yml entersys-prometheus:/etc/prometheus/prometheus.yml
        docker restart entersys-prometheus
    "
    exit 1
fi

log_success "Prometheus reiniciado exitosamente"

# Verificar que el target esté siendo monitoreado
log "Verificando target en Prometheus..."
sleep 5

TARGET_FOUND=""
for i in {1..10}; do
    if gcloud compute ssh dev-server --zone=us-central1-c --command="curl -s http://localhost:9090/api/v1/targets | grep -q '$SERVICE_URL'" 2>/dev/null; then
        TARGET_FOUND="true"
        break
    fi
    sleep 3
done

if [ "$TARGET_FOUND" != "true" ]; then
    log_warning "Target no encontrado inmediatamente en Prometheus, puede tomar unos minutos aparecer"
else
    log_success "Target detectado en Prometheus"
fi

# Generar configuración para Grafana
log "Generando configuración sugerida para panel de Grafana..."

cat << EOF > "/tmp/grafana-panel-$SERVICE_NAME.json"
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
      "expr": "probe_success{instance=\"$HEALTH_URL\"}",
      "legendFormat": "🔗 $SERVICE_NAME"
    }
  ],
  "title": "🔗 $(echo $SERVICE_NAME | tr '[:lower:]' '[:upper:]')",
  "type": "stat"
}
EOF

# Crear alertas sugeridas
log "Generando alertas Six Sigma sugeridas..."

cat << EOF > "/tmp/alerts-$SERVICE_NAME.yml"
# Alertas Six Sigma para $SERVICE_NAME
groups:
- name: ${SERVICE_NAME}-six-sigma
  rules:

  # Servicio DOWN
  - alert: ${SERVICE_NAME}ServiceDown
    expr: probe_success{instance="$HEALTH_URL"} == 0
    for: 10s
    labels:
      severity: critical
      service: $SERVICE_NAME
      sla: six-sigma
    annotations:
      summary: "$SERVICE_NAME está DOWN"
      description: "El servicio $SERVICE_NAME ha estado DOWN por más de 10 segundos."

  # Tiempo de respuesta alto
  - alert: ${SERVICE_NAME}HighResponseTime
    expr: probe_duration_seconds{instance="$HEALTH_URL"} > 3
    for: 2m
    labels:
      severity: warning
      service: $SERVICE_NAME
      sla: six-sigma
    annotations:
      summary: "Tiempo de respuesta alto en $SERVICE_NAME"
      description: "Tiempo de respuesta es {{ \$value }}s, excede el límite de 3s Six Sigma."
EOF

if [ ! -z "$CONTAINER_NAME" ]; then
cat << EOF >> "/tmp/alerts-$SERVICE_NAME.yml"

  # CPU alto en contenedor
  - alert: ${SERVICE_NAME}HighCPU
    expr: rate(container_cpu_usage_seconds_total{name="$CONTAINER_NAME"}[5m]) * 100 > 80
    for: 5m
    labels:
      severity: warning
      service: $SERVICE_NAME
    annotations:
      summary: "CPU alto en contenedor $CONTAINER_NAME"
      description: "Uso de CPU es {{ \$value }}%"

  # Memoria alta en contenedor
  - alert: ${SERVICE_NAME}HighMemory
    expr: (container_memory_usage_bytes{name="$CONTAINER_NAME"} / container_spec_memory_limit_bytes{name="$CONTAINER_NAME"}) * 100 > 80
    for: 5m
    labels:
      severity: warning
      service: $SERVICE_NAME
    annotations:
      summary: "Memoria alta en contenedor $CONTAINER_NAME"
      description: "Uso de memoria es {{ \$value }}%"
EOF
fi

# Crear script de verificación SLA
cat << EOF > "/tmp/check-sla-$SERVICE_NAME.sh"
#!/bin/bash
# Script de verificación SLA para $SERVICE_NAME

echo "🎯 VERIFICACIÓN SLA SIX SIGMA - $SERVICE_NAME"
echo "============================================="

# Prometheus URL
PROMETHEUS_URL="http://localhost:9090"

# Verificar disponibilidad 24h
uptime_24h=\$(curl -s "\$PROMETHEUS_URL/api/v1/query?query=avg_over_time(probe_success{instance=\"$HEALTH_URL\"}[24h])" | jq -r '.data.result[0].value[1] // "0"')

# Verificar tiempo de respuesta P95
response_time_p95=\$(curl -s "\$PROMETHEUS_URL/api/v1/query?query=quantile_over_time(0.95, probe_duration_seconds{instance=\"$HEALTH_URL\"}[24h])" | jq -r '.data.result[0].value[1] // "0"')

echo ""
echo "📊 MÉTRICAS ACTUALES:"
echo "  📈 Disponibilidad 24h: \$(printf "%.6f%%" \$(echo "\$uptime_24h * 100" | bc -l))"
echo "  ⚡ Tiempo respuesta P95: \$(printf "%.3fs" \$response_time_p95)"

echo ""
echo "🎯 OBJETIVOS SIX SIGMA:"
echo "  📈 Disponibilidad: >= 99.99966%"
echo "  ⚡ Tiempo respuesta: <= 3.000s"

echo ""
if (( \$(echo "\$uptime_24h >= 0.9999966" | bc -l) )); then
    echo "✅ DISPONIBILIDAD: SIX SIGMA COMPLIANT"
else
    echo "❌ DISPONIBILIDAD: SLA BREACH"
fi

if (( \$(echo "\$response_time_p95 <= 3" | bc -l) )); then
    echo "✅ TIEMPO RESPUESTA: SIX SIGMA COMPLIANT"
else
    echo "❌ TIEMPO RESPUESTA: SLA BREACH"
fi

echo ""
echo "📊 Dashboard: https://monitoring.entersys.mx/d/entersys-3s/"
EOF

chmod +x "/tmp/check-sla-$SERVICE_NAME.sh"

# Resumen final
echo ""
echo -e "${GREEN}🎉 =================================="
echo "   CONFIGURACIÓN COMPLETADA"
echo "=================================="
echo -e "${NC}"

log_success "$SERVICE_NAME agregado exitosamente al monitoreo Six Sigma"
echo ""
echo -e "${BLUE}📊 RECURSOS GENERADOS:${NC}"
echo "  🔧 Panel Grafana: /tmp/grafana-panel-$SERVICE_NAME.json"
echo "  🚨 Alertas: /tmp/alerts-$SERVICE_NAME.yml"
echo "  📈 Script SLA: /tmp/check-sla-$SERVICE_NAME.sh"
echo ""
echo -e "${BLUE}🌐 ACCESO AL SISTEMA:${NC}"
echo "  📊 Dashboard Principal: https://monitoring.entersys.mx/d/entersys-3s/"
echo "  📈 Prometheus: https://monitoring.entersys.mx:9090"
echo "  🎯 Grafana (admin/admin123): https://monitoring.entersys.mx"
echo ""
echo -e "${BLUE}🔍 VERIFICACIÓN:${NC}"
echo "  • Health Check: $HEALTH_URL"
echo "  • Target Status: https://monitoring.entersys.mx:9090/targets"
if [ ! -z "$CONTAINER_NAME" ]; then
echo "  • Container: docker logs $CONTAINER_NAME"
fi
echo ""
echo -e "${YELLOW}⚠️  PRÓXIMOS PASOS:${NC}"
echo "  1. Agregar panel de Grafana usando el JSON generado"
echo "  2. Configurar alertas usando el archivo YAML generado"
echo "  3. Ejecutar script de verificación SLA: /tmp/check-sla-$SERVICE_NAME.sh"
echo "  4. Validar que métricas aparezcan en 2-3 minutos"
echo ""

# Ejecutar verificación SLA automáticamente en 30 segundos
echo -e "${BLUE}🕒 Ejecutando verificación SLA en 30 segundos...${NC}"
sleep 30

if gcloud compute ssh dev-server --zone=us-central1-c < "/tmp/check-sla-$SERVICE_NAME.sh"; then
    log_success "Verificación SLA completada"
else
    log_warning "Verificación SLA falló, el servicio podría necesitar más tiempo para aparecer"
fi

echo ""
log_success "🎯 MONITOREO SIX SIGMA CONFIGURADO EXITOSAMENTE"
echo ""