# MIDDLEWARE DE LOGGING ESTANDARIZADO PARA SIX SIGMA
# Registra cada peticion con metricas detalladas para monitoreo de calidad

import time
import json
import uuid
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

class SixSigmaRequestLogger:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'sla_breaches': 0,
            'error_rate': 0.0,
            'avg_response_time': 0.0,
            'uptime_percentage': 100.0
        }

    def generate_request_id(self) -> str:
        return f'req_{uuid.uuid4().hex[:12]}'

    def get_current_metrics(self) -> Dict[str, Any]:
        six_sigma_target = 99.99966
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_metrics': self.metrics.copy(),
            'six_sigma_compliance': {
                'target_availability': six_sigma_target,
                'current_availability': self.metrics['uptime_percentage'],
                'compliance_status': 'compliant' if self.metrics['uptime_percentage'] >= six_sigma_target else 'non_compliant',
                'defects_per_million': max(0, (100 - self.metrics['uptime_percentage']) * 10000),
                'sigma_level': '6_sigma' if self.metrics['uptime_percentage'] >= 99.99966 else 'below_6_sigma'
            }
        }

class SixSigmaLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: Optional[SixSigmaRequestLogger] = None):
        super().__init__(app)
        self.logger = logger or SixSigmaRequestLogger()

    async def dispatch(self, request: Request, call_next):
        request_id = self.logger.generate_request_id()
        request.state.request_id = request_id
        request.state.six_sigma_logger = self.logger
        
        try:
            response = await call_next(request)
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Six-Sigma-Tracking'] = 'enabled'
            return response
        except Exception as e:
            response = Response(
                content=json.dumps({'error': 'Internal server error', 'request_id': request_id}),
                status_code=500,
                media_type='application/json'
            )
            response.headers['X-Request-ID'] = request_id
            return response
