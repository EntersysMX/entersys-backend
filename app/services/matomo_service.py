import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

class MatomoService:
    def __init__(self):
        self.base_url = getattr(settings, 'MATOMO_API_URL', 'https://analytics.entersys.mx')
        self.site_id = getattr(settings, 'MATOMO_SITE_ID', '1')
        self.auth_token = getattr(settings, 'MATOMO_AUTH_TOKEN', '3ac3a24ea144186278aa48054603aaaa')

    async def track_event(
        self,
        category: str,
        action: str,
        name: Optional[str] = None,
        value: Optional[float] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía un evento a Matomo Analytics
        """
        try:
            params = {
                'rec': 1,
                'idsite': self.site_id,
                'action_name': f"Event: {category}",
                'url': url or 'https://dev.entersys.mx',
                'e_c': category,
                'e_a': action,
                'token_auth': self.auth_token,
                'cdt': datetime.now().isoformat(),
                'send_image': 0
            }

            if name:
                params['e_n'] = name
            if value:
                params['e_v'] = value

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/matomo.php", params=params)

            return {
                'success': True,
                'status_code': response.status_code,
                'event_type': 'event'
            }

        except Exception as e:
            logger.error(f"Error tracking event: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'event_type': 'event'
            }

    async def track_goal(
        self,
        goal_id: int,
        revenue: Optional[float] = None,
        url: Optional[str] = None,
        action_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía una conversión de goal a Matomo Analytics
        """
        try:
            params = {
                'rec': 1,
                'idsite': self.site_id,
                'idgoal': goal_id,
                'url': url or 'https://dev.entersys.mx',
                'action_name': action_name or f"Goal {goal_id} Conversion",
                'token_auth': self.auth_token,
                'cdt': datetime.now().isoformat()
            }

            if revenue:
                params['revenue'] = revenue

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/matomo.php", params=params)

            return {
                'success': True,
                'status_code': response.status_code,
                'event_type': 'goal'
            }

        except Exception as e:
            logger.error(f"Error tracking goal: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'event_type': 'goal'
            }

    async def track_lead_capture(
        self,
        lead_data: Dict[str, Any],
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trackea específicamente la captura de leads
        """
        try:
            # Trackear evento de formulario
            event_result = await self.track_event(
                category="Form",
                action="Submit",
                name=f"Lead Form - {lead_data.get('interest', 'unknown')}",
                value=1,
                url=url
            )

            # Trackear conversión (Goal ID 1)
            goal_result = await self.track_goal(
                goal_id=1,
                revenue=50.0,
                url=url,
                action_name=f"Lead Captured - {lead_data.get('interest', 'unknown')}"
            )

            return {
                'event_tracking': event_result,
                'goal_tracking': goal_result,
                'lead_data': {
                    'name': lead_data.get('name'),
                    'email': lead_data.get('email'),
                    'interest': lead_data.get('interest')
                }
            }

        except Exception as e:
            logger.error(f"Error tracking lead capture: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Instancia global del servicio
matomo_service = MatomoService()