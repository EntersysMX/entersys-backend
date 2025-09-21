from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class LeadCaptureSchema(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = ""
    phone: Optional[str] = ""
    interest: str
    message: Optional[str] = ""
    source: str = "website_form"

@router.post("/lead-capture")
async def capture_lead(lead_data: LeadCaptureSchema, request: Request):
    try:
        # Configuración directa de Matomo
        base_url = "https://analytics.entersys.mx"
        site_id = "1"
        auth_token = "3ac3a24ea144186278aa48054603aaaa"

        # Tracking evento de formulario
        event_params = {
            'rec': 1,
            'idsite': site_id,
            'action_name': f"Event: Form",
            'url': str(request.url),
            'e_c': "Form",
            'e_a': "Submit",
            'e_n': f"Lead Form - {lead_data.interest}",
            'e_v': 1,
            'token_auth': auth_token,
            'cdt': datetime.now().isoformat(),
            'send_image': 0
        }

        # Tracking conversión
        conversion_params = {
            'rec': 1,
            'idsite': site_id,
            'idgoal': 1,
            'revenue': 50.0,
            'url': str(request.url),
            'action_name': f"Conversion: Lead Captured - {lead_data.interest}",
            'token_auth': auth_token,
            'cdt': datetime.now().isoformat()
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Enviar evento
            event_response = await client.get(f"{base_url}/matomo.php", params=event_params)
            # Enviar conversión
            conversion_response = await client.get(f"{base_url}/matomo.php", params=conversion_params)

        return {
            "success": True,
            "message": "Lead captured and tracked successfully",
            "lead": {
                "name": lead_data.name,
                "email": lead_data.email,
                "company": lead_data.company,
                "interest": lead_data.interest
            },
            "tracking": {
                "event_status": event_response.status_code,
                "conversion_status": conversion_response.status_code
            }
        }
    except Exception as e:
        logger.error(f"Error capturing lead: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error capturing lead: {str(e)}")