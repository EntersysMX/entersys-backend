from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
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
async def capture_lead(lead_data: LeadCaptureSchema, request: Request, background_tasks: BackgroundTasks):
    """
    Capturar lead con tracking completo y sincronización CRM

    **Flujo completo:**
    1. Tracking inmediato en Matomo
    2. Sincronización con Mautic CRM (background)
    3. Respuesta rápida al cliente
    """
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

        # *** NUEVO *** Sincronización con CRM en background
        background_tasks.add_task(sync_lead_to_crm_background, lead_data.dict())

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
            },
            "crm_sync": "scheduled_background"
        }
    except Exception as e:
        logger.error(f"Error capturing lead: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error capturing lead: {str(e)}")

# *** NUEVO *** Background task para sincronización CRM
async def sync_lead_to_crm_background(lead_data: dict):
    """Sincronizar lead con Mautic CRM en background"""
    try:
        # Import dinámico para evitar dependencias circulares
        from app.services.mautic_service import MauticService

        mautic_service = MauticService()

        # Verificar si contacto existe
        existing_contact = await mautic_service.get_contact_by_email(lead_data['email'])

        if existing_contact.get("found"):
            # Actualizar score por re-engagement
            await mautic_service.update_contact_score(
                email=lead_data['email'],
                score_delta=5,
                action=f"form_resubmit_{lead_data['interest']}"
            )
            logger.info(f"CRM: Lead existente re-activado - {lead_data['email']}")
        else:
            # Crear nuevo contacto
            result = await mautic_service.create_contact(lead_data)
            if result.get("success"):
                logger.info(f"CRM: Nuevo lead sincronizado - {lead_data['email']} -> ID {result['contact_id']}")
            else:
                logger.error(f"CRM: Error sincronizando lead - {result.get('error')}")

    except Exception as e:
        logger.error(f"Error en background sync CRM: {str(e)}")