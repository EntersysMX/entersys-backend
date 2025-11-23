# 📊 Six Sigma Dashboards - Entersys

Suite completa de dashboards especializados para monitoreo Six Sigma con análisis avanzado de calidad, performance y compliance.

## 🎯 Dashboards Incluidos

### 1. 📊 Six Sigma Analytics - Main Dashboard
**Archivo:** `six-sigma-analytics-main.json`

**Propósito:** Dashboard principal con overview completo de métricas Six Sigma

**Paneles Clave:**
- 🎯 Six Sigma Compliance Overview
- ⚡ Response Time Distribution (< 1s, 1-3s, > 3s)
- 🚨 Error Rate by Service
- 📈 Quality Level Trends (Pie Chart)
- 🔍 Real-Time Six Sigma Requests
- 📊 SLA Compliance by Endpoint
- 🌡️ Performance Heatmap
- 📋 Recent Six Sigma Events (Log Stream)

**Métricas:**
- Quality level distribution (six_sigma, five_sigma, etc.)
- SLA compliance rates por endpoint
- Performance categorization (excellent, good, poor)
- Real-time events stream

---

### 2. ⚡ Six Sigma Performance & SLA Dashboard
**Archivo:** `six-sigma-performance-sla.json`

**Propósito:** Análisis detallado de performance y compliance SLA

**Paneles Clave:**
- 🎯 SLA Compliance Rate (Gauge)
- ⏱️ Response Time P95
- 🚀 Average Response Time
- 📊 Performance Score Distribution
- 📈 Response Time Trends by Service
- 🚨 SLA Breaches Timeline
- 🔥 Top Slowest Endpoints
- ⭐ Performance Categories
- 📊 SLA Compliance by Service (Bar Gauge)

**Thresholds:**
- SLA Target: 99.99966%
- Response Time Target: ≤ 3000ms
- Performance Categories: Excellent (90-100), Good (75-89), Average (50-74), Poor (<50)

---

### 3. 🚨 Six Sigma Error Analysis & Quality Dashboard
**Archivo:** `six-sigma-error-analysis.json`

**Propósito:** Análisis profundo de errores, defectos y métricas de calidad

**Paneles Clave:**
- 🎯 Error Rate (PPM - Parts Per Million)
- 📊 Current Sigma Level (Gauge dinámico)
- 🚀 Success Rate
- ⚡ Defect Count
- 📈 Error Rate Trends by Service
- 🔍 Defect Types Distribution
- 🚨 Error Details Log Stream
- 📊 Quality Level Progression
- 🔥 Critical Issues (Last 24h)
- 📈 DPMO Trend (Defects Per Million Opportunities)

**Six Sigma Levels:**
- Six Sigma: 99.99966% (3.4 PPM)
- Five Sigma: 99.977% (233 PPM)
- Four Sigma: 99.38% (6,210 PPM)
- Three Sigma: 93.32% (66,807 PPM)

---

### 4. 🏆 Six Sigma Executive Dashboard
**Archivo:** `six-sigma-executive.json`

**Propósito:** Dashboard ejecutivo con KPIs de alto nivel y métricas de negocio

**Paneles Clave:**
- 🎯 Six Sigma Score (Gauge principal)
- 💼 Business Impact KPIs (Table)
- 📊 Monthly Quality Trend
- 🏅 Quality Certification Status
- 💰 Cost of Poor Quality
- 🚀 Service Excellence Matrix (Heatmap)
- 📈 Performance vs. Availability Scatter
- 🎯 Key Performance Indicators
- 📊 Process Capability (Cpk)

**Business Metrics:**
- Six Sigma Achievement %
- Estimated cost impact of errors
- Process capability index (Cpk)
- Quality certification status

---

## 🚀 Instalación

### Opción 1: Deploy Automático
```bash
# Ejecutar script de deploy automático
./deploy-six-sigma-dashboards.sh

# Con preview (dry-run)
./deploy-six-sigma-dashboards.sh --dry-run

# Forzar reemplazo de dashboards existentes
./deploy-six-sigma-dashboards.sh --force
```

### Opción 2: Importación Manual
1. Acceder a Grafana: `https://monitoring.entersys.mx`
2. Ir a "+" → "Import"
3. Subir cada archivo JSON
4. Seleccionar datasource: **Loki**
5. Configurar folder: **Six Sigma**

---

## 📊 Configuración de Datasources

### Loki (Principal)
```yaml
URL: http://loki:3100
Access: Server (Default)
```

### Prometheus (Complementario)
```yaml
URL: http://prometheus:9090
Access: Server (Default)
```

---

## 🎯 Queries Principales

### Six Sigma Quality Level
```logql
{logger="six_sigma.requests"} | json | quality_level="six_sigma"
```

### SLA Compliance
```logql
{logger="six_sigma.requests"} | json | sla_compliant="true"
```

### Error Rate (PPM)
```logql
(sum(rate({level="ERROR"} [5m])) / sum(rate({level=~"INFO|WARN|ERROR"} [5m]))) * 1000000
```

### Performance Categories
```logql
{logger="six_sigma.performance"} | json | performance_category != ""
```

---

## 🔧 Personalización

### Agregar Nuevos Servicios
1. Los servicios se detectan automáticamente desde logs
2. Usar variable `$service` en queries
3. Filtros se actualizan dinámicamente

### Modificar Thresholds
```json
{
  "thresholds": {
    "steps": [
      {"color": "green", "value": null},
      {"color": "yellow", "value": 95},
      {"color": "red", "value": 99.99966}
    ]
  }
}
```

### Alertas Personalizadas
```json
{
  "name": "SLA Breaches",
  "enable": true,
  "iconColor": "red",
  "query": "{logger=\"six_sigma.sla\"} | json | sla_compliant=\"false\"",
  "textFormat": "SLA Breach: {{service}} - {{duration_ms}}ms"
}
```

---

## 📋 Variables de Dashboard

### service
```logql
label_values({logger="six_sigma.requests"}, service)
```

### quality_level
```logql
label_values({logger="six_sigma.requests"}, quality_level)
```

### error_type
```logql
label_values({logger="six_sigma.requests"}, error_type)
```

---

## 🎨 Refresh Rates

| Dashboard | Refresh Rate | Razón |
|-----------|--------------|-------|
| Main | 10s | Overview en tiempo real |
| Performance | 5s | Métricas críticas de performance |
| Error Analysis | 10s | Análisis detallado de errores |
| Executive | 30s | KPIs de alto nivel |

---

## 🔍 Troubleshooting

### Dashboard No Muestra Datos
1. Verificar que Loki esté corriendo: `curl http://loki:3100/ready`
2. Verificar logs Six Sigma: `ls -la logs/six_sigma_*.log`
3. Verificar timerange del dashboard

### Queries Lentas
1. Reducir timerange
2. Usar filtros de servicio específico
3. Verificar índices en Loki

### Métricas Incorrectas
1. Verificar formato de logs Six Sigma
2. Verificar estructura JSON en logs
3. Validar middleware de logging está activo

---

## 📚 Referencias

- **Six Sigma Standards**: 99.99966% availability (3.4 PPM defects)
- **Loki Documentation**: [Grafana Loki Docs](https://grafana.com/docs/loki/)
- **LogQL Reference**: [LogQL Syntax](https://grafana.com/docs/loki/latest/logql/)
- **Entersys Monitoring**: `https://monitoring.entersys.mx`

---

## 🤝 Contribución

Para agregar nuevos dashboards o mejorar existentes:

1. Crear JSON siguiendo estructura estándar
2. Añadir al array `DASHBOARDS` en `deploy-six-sigma-dashboards.sh`
3. Actualizar este README
4. Probar con `--dry-run` antes de deploy

---

## 📄 Licencia

Dashboards desarrollados para Entersys.mx - Uso interno

**Contacto:** armandocortes@entersys.mx