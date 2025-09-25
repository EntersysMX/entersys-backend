# 📊 CÓMO AGREGAR ENTERSYS API AL DASHBOARD GRAFANA

## 🎯 **Dashboard:** https://monitoring.entersys.mx/d/entersys-3s/f09f8eaf-entersys-metodo-3-segundos

## 🔧 **PASO 1: Agregar Panel de Estado API**

1. Click en **"+ Add Panel"** en el dashboard
2. Selecciona **"Stat"** como tipo de visualización
3. En **Query**, usa:
   ```promql
   probe_success{instance="https://api.dev.entersys.mx/api/v1/health"}
   ```
4. **Título:** `🔗 Entersys API - Smartsheet Service`
5. **Thresholds:**
   - `0` = Red (DOWN)
   - `1` = Green (UP)
6. **Mappings:**
   - `0` → `DOWN`
   - `1` → `UP`

## 📋 **PASO 2: Agregar Panel de Logs**

1. Agregar nuevo panel tipo **"Logs"**
2. **Datasource:** Loki (si disponible)
3. **Query:**
   ```logql
   {container_name="entersys-content-api"}
   ```
4. **Título:** `📋 Entersys API - Logs Monitor`
5. **Filtros adicionales:**
   - Errores: `{container_name="entersys-content-api"} |= "ERROR"`
   - Smartsheet ops: `{container_name="entersys-content-api"} |= "smartsheet"`

## 📈 **PASO 3: Métricas del Contenedor**

### Panel CPU Usage:
```promql
rate(container_cpu_usage_seconds_total{name="entersys-content-api"}[5m]) * 100
```

### Panel Memory Usage:
```promql
container_memory_usage_bytes{name="entersys-content-api"} / 1024 / 1024
```

### Panel Response Time:
```promql
probe_duration_seconds{instance="https://api.dev.entersys.mx/api/v1/health"}
```

## 🚨 **PASO 4: Alertas** (Opcional)

### Alert Rule para API Down:
```promql
probe_success{instance="https://api.dev.entersys.mx/api/v1/health"} == 0
```

## 📊 **VERIFICACIÓN DE SERVICIOS:**

### ✅ **Servicios Monitoreados:**
- **API Health:** `https://api.dev.entersys.mx/api/v1/health` ✅
- **Container:** `entersys-content-api` ✅
- **Logs:** Estructurados JSON con rotación ✅
- **Smartsheet Service:** Integrado y funcional ✅

### 📍 **Contenedores API Disponibles:**
- `entersys-content-api` (Principal - USAR ESTE)
- `dev-entersys-backend` (Alternativo)

### 🔗 **URLs de Verificación:**
```bash
# Health Check
curl https://api.dev.entersys.mx/api/v1/health

# Documentación
https://api.dev.entersys.mx/docs

# Logs en servidor
docker logs entersys-content-api --tail 50
```

## 🎨 **Layout Sugerido:**

```
[🔗 API Status] [📊 CPU %] [💾 Memory MB]
[📋 API Logs Panel (full width)      ]
[📈 Response Time] [🔄 Request Rate   ]
```

## ⚡ **Queries Importantes:**

1. **Estado UP/DOWN:**
   ```promql
   probe_success{instance="https://api.dev.entersys.mx/api/v1/health"}
   ```

2. **Logs de Errores:**
   ```logql
   {container_name="entersys-content-api"} |= "ERROR"
   ```

3. **Operaciones Smartsheet:**
   ```logql
   {container_name="entersys-content-api"} |= "smartsheet"
   ```

## 🚀 **El servicio está LISTO y funcionando.**

### ✅ **Status:** API operativo con logs estructurados
### ✅ **Monitoreo:** Métricas y logs disponibles
### ✅ **Dashboard:** Listo para integrar