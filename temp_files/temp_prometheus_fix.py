# Temporary fix for prometheus metrics duplication
from prometheus_client import Counter, Histogram, Gauge, REGISTRY

# Initialize variables
API_REQUESTS_TOTAL = None
API_REQUEST_DURATION = None  
SMARTSHEET_OPERATIONS_TOTAL = None
SMARTSHEET_ACTIVE_CONNECTIONS = None

try:
    # Check if metrics already exist
    existing_metrics = [collector._name for collector in REGISTRY._collector_to_names.keys() if hasattr(collector, '_name')]
    
    if 'api_requests_total' not in existing_metrics:
        API_REQUESTS_TOTAL = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status']
        )
    
    if 'api_request_duration_seconds' not in existing_metrics:
        API_REQUEST_DURATION = Histogram(
            'api_request_duration_seconds',
            'Time spent processing API requests',
            ['method', 'endpoint']
        )
    
    if 'smartsheet_operations_total' not in existing_metrics:
        SMARTSHEET_OPERATIONS_TOTAL = Counter(
            'smartsheet_operations_total',
            'Total number of Smartsheet operations',
            ['operation', 'status']
        )
    
    if 'smartsheet_active_connections' not in existing_metrics:
        SMARTSHEET_ACTIVE_CONNECTIONS = Gauge(
            'smartsheet_active_connections',
            'Number of active connections to Smartsheet API'
        )

except Exception as e:
    # If there's any issue, just set to None
    print(f"Prometheus metrics setup failed: {e}")
    API_REQUESTS_TOTAL = None
    API_REQUEST_DURATION = None
    SMARTSHEET_OPERATIONS_TOTAL = None
    SMARTSHEET_ACTIVE_CONNECTIONS = None
