from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import os

router = APIRouter()

# Métricas de Prometheus para el API
entersys_api_requests_total = Counter(
    'entersys_api_requests_total',
    'Total Entersys API requests',
    ['method', 'endpoint', 'status']
)

entersys_api_request_duration_seconds = Histogram(
    'entersys_api_request_duration_seconds',
    'Entersys API request duration in seconds',
    ['method', 'endpoint']
)

smartsheet_operations_total = Counter(
    'smartsheet_operations_total',
    'Total Smartsheet operations',
    ['operation', 'status']
)

smartsheet_active_connections = Gauge(
    'smartsheet_active_connections',
    'Active Smartsheet connections'
)

# Métricas del sistema
system_uptime_seconds = Gauge(
    'system_uptime_seconds',
    'System uptime in seconds'
)

# Inicializar métricas del sistema
start_time = time.time()
smartsheet_active_connections.set(1)  # Una conexión activa por defecto

@router.get("/metrics", include_in_schema=False)
def get_metrics():
    """
    Endpoint de métricas para Prometheus.
    No incluido en la documentación de la API.
    """
    # Actualizar uptime
    system_uptime_seconds.set(time.time() - start_time)

    # Generar métricas en formato Prometheus
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )