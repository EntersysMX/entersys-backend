from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr
from app.services.mautic_service import MauticService
from app.services.matomo_service import MatomoService  # Ya existe
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas específicos para CRM
class LeadSyncSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    company: Optional[str] = Field("", max_length=100)
    phone: Optional[str] = Field("", max_length=20)
    interest: str = Field(..., pattern="^(general|worksys|expersys|demo|partnership|automation)$")
    message: Optional[str] = Field("", max_length=500)
    source: str = Field("website_form", max_length=50)

class ScoreUpdateSchema(BaseModel):
    action: str = Field(..., description="Acción que genera el score")
    score_delta: int = Field(..., ge=-50, le=50, description="Cambio en el score")
    metadata: Optional[Dict[str, Any]] = Field({})

class CampaignTriggerSchema(BaseModel):
    email: EmailStr
    campaign_type: str = Field(..., pattern="^(welcome_general|welcome_worksys|welcome_expersys|welcome_demo|nurturing_.+)$")
    trigger_data: Optional[Dict[str, Any]] = Field({})

@router.post("/sync-lead", summary="Sincronizar lead con Mautic CRM")
async def sync_lead_to_crm(
    lead_data: LeadSyncSchema,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Sincronizar lead con Mautic CRM y disparar workflows automáticos

    **Flujo completo:**
    1. Verificar si contacto existe en Mautic
    2. Crear o actualizar contacto
    3. Asignar score inicial
    4. Asignar a segmento correspondiente
    5. Disparar campaña de bienvenida
    6. Tracking en Matomo (background)
    """
    try:
        mautic_service = MauticService()

        # 1. Verificar si contacto ya existe
        existing_contact = await mautic_service.get_contact_by_email(lead_data.email)

        if existing_contact.get("found"):
            # Contacto existe - actualizar score por re-engagement
            score_result = await mautic_service.update_contact_score(
                email=lead_data.email,
                score_delta=5,
                action=f"form_resubmit_{lead_data.interest}"
            )

            logger.info(f"Lead existente re-activado: {lead_data.email}")

            return {
                "success": True,
                "action": "updated",
                "contact_id": existing_contact['contact']['id'],
                "score_update": score_result,
                "message": "Contacto existente actualizado y re-activado"
            }
        else:
            # 2. Crear nuevo contacto
            create_result = await mautic_service.create_contact(lead_data.dict())

            if not create_result.get("success"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Error creando contacto en CRM: {create_result.get('error')}"
                )

            contact_id = create_result['contact_id']

            # 3. Disparar campaña de bienvenida (background)
            background_tasks.add_task(
                trigger_welcome_campaign_background,
                lead_data.email,
                lead_data.interest
            )

            # 4. Tracking en Matomo (background)
            background_tasks.add_task(
                track_crm_sync_background,
                lead_data.dict(),
                str(request.url)
            )

            logger.info(f"Nuevo lead sincronizado con CRM: {lead_data.email} -> Contact ID {contact_id}")

            return {
                "success": True,
                "action": "created",
                "contact_id": contact_id,
                "message": "Lead sincronizado exitosamente con CRM",
                "next_steps": [
                    "Campaña de bienvenida programada",
                    "Asignado a segmento correspondiente",
                    "Tracking configurado"
                ]
            }

    except Exception as e:
        logger.error(f"Error sincronizando lead con CRM: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error de sincronización CRM: {str(e)}")

@router.post("/lead/{email}/score", summary="Actualizar lead score por comportamiento")
async def update_lead_score(
    email: str,
    score_data: ScoreUpdateSchema,
    request: Request
):
    """
    Actualizar lead score basado en comportamiento web

    **Acciones de scoring:**
    - whatsapp_click: +5 puntos
    - page_solutions_visit: +3 puntos
    - page_pricing_visit: +8 puntos
    - email_open: +2 puntos
    - email_click: +5 puntos
    - resource_download: +15 puntos
    """
    try:
        mautic_service = MauticService()

        result = await mautic_service.update_contact_score(
            email=email,
            score_delta=score_data.score_delta,
            action=score_data.action
        )

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Contacto no encontrado en CRM")

        # Track score update en Matomo
        matomo_service = MatomoService()
        await matomo_service.track_event({
            "category": "CRM",
            "action": "Score_Update",
            "name": f"{score_data.action} -> {score_data.score_delta}pts",
            "value": abs(score_data.score_delta),
            "url": str(request.url)
        })

        return {
            "success": True,
            "email": email,
            "score_change": {
                "action": score_data.action,
                "delta": score_data.score_delta,
                "old_score": result['old_score'],
                "new_score": result['new_score']
            },
            "qualification_status": get_qualification_status(result['new_score'])
        }

    except Exception as e:
        logger.error(f"Error actualizando score para {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaign/trigger", summary="Disparar campaña de nurturing")
async def trigger_nurturing_campaign(
    campaign_data: CampaignTriggerSchema,
    request: Request
):
    """Disparar campaña específica de nurturing"""
    try:
        mautic_service = MauticService()

        result = await mautic_service.trigger_email_campaign(
            email=campaign_data.email,
            campaign_type=campaign_data.campaign_type
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Error disparando campaña: {result.get('error')}"
            )

        return {
            "success": True,
            "campaign_triggered": campaign_data.campaign_type,
            "contact_id": result['contact_id'],
            "trigger_time": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error disparando campaña: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lead/{email}/profile", summary="Obtener perfil completo del lead")
async def get_lead_profile(email: str):
    """Obtener perfil completo del lead desde Mautic"""
    try:
        mautic_service = MauticService()

        result = await mautic_service.get_contact_by_email(email)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Error consultando CRM")

        if not result.get("found"):
            raise HTTPException(status_code=404, detail="Lead no encontrado")

        contact = result['contact']

        return {
            "success": True,
            "profile": {
                "id": contact.get('id'),
                "name": f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip(),
                "email": contact.get('email'),
                "company": contact.get('company'),
                "phone": contact.get('phone'),
                "score": int(contact.get('points', 0)),
                "qualification": get_qualification_status(int(contact.get('points', 0))),
                "source": contact.get('lead_source'),
                "interest": contact.get('lead_interest'),
                "date_added": contact.get('date_added'),
                "last_activity": contact.get('last_activity'),
                "tags": contact.get('tags', [])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo perfil de {email}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/leads-summary", summary="Resumen de leads para dashboard")
async def get_leads_summary():
    """Resumen ejecutivo de leads para dashboard administrativo"""
    try:
        mautic_service = MauticService()

        # Obtener estadísticas básicas (implementar según API de Mautic)
        # Por ahora retornamos estructura de ejemplo

        return {
            "success": True,
            "summary": {
                "total_leads": 0,  # TODO: Implementar conteo real
                "mql_count": 0,    # Marketing Qualified Leads
                "sql_count": 0,    # Sales Qualified Leads
                "avg_score": 0,    # Score promedio
                "top_sources": [   # Fuentes principales
                    {"source": "website_form", "count": 0},
                    {"source": "whatsapp", "count": 0}
                ],
                "top_interests": [ # Intereses principales
                    {"interest": "demo", "count": 0},
                    {"interest": "worksys", "count": 0}
                ]
            },
            "period": "last_30_days",
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen de leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def trigger_welcome_campaign_background(email: str, interest: str):
    """Disparar campaña de bienvenida en background"""
    try:
        mautic_service = MauticService()
        campaign_type = f"welcome_{interest}"

        await asyncio.sleep(2)  # Delay para asegurar que el contacto esté creado

        result = await mautic_service.trigger_email_campaign(email, campaign_type)

        if result.get("success"):
            logger.info(f"Campaña de bienvenida disparada: {email} -> {campaign_type}")
        else:
            logger.warning(f"Error disparando campaña de bienvenida: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error en background task de campaña: {str(e)}")

async def track_crm_sync_background(lead_data: dict, url: str):
    """Tracking de sincronización CRM en background"""
    try:
        matomo_service = MatomoService()

        await matomo_service.track_event({
            "category": "CRM",
            "action": "Lead_Synced",
            "name": f"CRM Sync - {lead_data.get('interest', 'unknown')}",
            "value": 1,
            "url": url
        })

        # También tracking de conversión
        await matomo_service.track_conversion({
            "goal_id": 1,  # Lead capture goal
            "conversion_name": f"CRM Lead Sync - {lead_data.get('interest')}",
            "revenue": 25.0,
            "url": url
        })

    except Exception as e:
        logger.error(f"Error tracking CRM sync: {str(e)}")

def get_qualification_status(score: int) -> str:
    """Determinar estatus de calificación basado en score"""
    if score >= 80:
        return "SQL"  # Sales Qualified Lead
    elif score >= 50:
        return "MQL"  # Marketing Qualified Lead
    elif score >= 20:
        return "WARM"  # Lead tibio
    else:
        return "COLD"  # Lead frío