# app/api/v1/endpoints/smartsheet_webhook.py
from fastapi import APIRouter, Header, Depends, HTTPException, Request, status
from typing import Optional, List
import logging
import httpx

from app.core.config import settings
from app.services.onboarding_smartsheet_service import (
    OnboardingSmartsheetService,
    OnboardingSmartsheetServiceError,
)
from app.api.v1.endpoints.onboarding import resend_approved_certificate_email

router = APIRouter()
logger = logging.getLogger(__name__)

# Sheet ID de Registros (misma constante que en el servicio)
SHEET_REGISTROS_ID = OnboardingSmartsheetService.SHEET_REGISTROS_ID


def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Valida la API key del middleware."""
    if x_api_key != settings.MIDDLEWARE_API_KEY:
        logger.warning(f"Smartsheet webhook: invalid API key attempted: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


def get_onboarding_service() -> OnboardingSmartsheetService:
    return OnboardingSmartsheetService()


# ──────────────────────────────────────────────
# POST /callback  –  Webhook callback de Smartsheet
# ──────────────────────────────────────────────
@router.post(
    "/callback",
    summary="Callback del webhook de Smartsheet",
    description="Recibe notificaciones de cambios en la hoja de Registros. "
    "Detecta cambios en la columna 'Correo Electronico' y reenvia "
    "el certificado al nuevo correo automaticamente.",
)
async def webhook_callback(request: Request):
    """
    Callback que Smartsheet invoca cuando hay cambios en la hoja.

    Fase 1 – Verificacion (challenge):
        Smartsheet envia el header `Smartsheet-Hook-Challenge`.
        Se responde con {"smartsheetHookResponse": challenge}.
        NO se valida API key en esta fase porque Smartsheet no envia headers custom.

    Fase 2 – Eventos:
        Smartsheet NO envia headers custom en los eventos, por lo que la
        autenticacion se hace validando que el scopeObjectId del payload
        coincida con SHEET_REGISTROS_ID (solo nuestra hoja genera eventos).
    """

    # ── Fase de verificacion (challenge) ──
    challenge = request.headers.get("Smartsheet-Hook-Challenge")
    if challenge:
        logger.info("Smartsheet webhook: challenge received, responding")
        return {"smartsheetHookResponse": challenge}

    # ── Parsear body ──
    try:
        body = await request.json()
    except Exception:
        logger.error("Smartsheet webhook: could not parse request body")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validar que el evento sea de la hoja correcta (autenticacion por scopeObjectId)
    scope_object_id = body.get("scopeObjectId")
    if not scope_object_id or int(scope_object_id) != SHEET_REGISTROS_ID:
        logger.warning(
            f"Smartsheet webhook: event for unexpected sheet {scope_object_id}, ignoring"
        )
        return {"status": "ignored", "reason": "wrong sheet"}

    events: List[dict] = body.get("events", [])
    if not events:
        logger.debug("Smartsheet webhook: no events in payload")
        return {"status": "ok", "processed": 0}

    # ── Obtener column IDs de las columnas que disparan reenvio ──
    service = get_onboarding_service()
    await service._get_registros_column_maps()
    correo_column_id = service.get_correo_electronico_column_id()
    reenviar_column_id = service.get_reenviar_correo_column_id()

    trigger_column_ids = set()
    if correo_column_id:
        trigger_column_ids.add(correo_column_id)
    if reenviar_column_id:
        trigger_column_ids.add(reenviar_column_id)

    if not trigger_column_ids:
        logger.error("Smartsheet webhook: could not resolve trigger column IDs")
        return {"status": "error", "reason": "column_ids_not_found"}

    # ── Filtrar eventos: cambios en "Correo Electronico" o "Reenviar correo" ──
    email_changed_rows = set()
    reenviar_changed_rows = set()
    for event in events:
        if event.get("objectType") != "cell" or event.get("eventType") != "updated":
            continue
        col_id = event.get("columnId")
        if col_id == correo_column_id:
            email_changed_rows.add(event["rowId"])
        elif col_id == reenviar_column_id:
            reenviar_changed_rows.add(event["rowId"])

    affected_row_ids = email_changed_rows | reenviar_changed_rows

    if not affected_row_ids:
        logger.debug("Smartsheet webhook: no trigger column changes detected")
        return {"status": "ok", "processed": 0}

    logger.info(
        f"Smartsheet webhook: {len(affected_row_ids)} rows with trigger column change detected "
        f"(email={len(email_changed_rows)}, reenviar={len(reenviar_changed_rows)})"
    )

    # ── Procesar cada fila afectada ──
    processed = 0
    for row_id in affected_row_ids:
        try:
            row_data = await service.get_row_data_by_id(row_id)
            if row_data is None:
                logger.warning(f"Smartsheet webhook: could not read row {row_id}")
                continue

            # Verificar que tenga resultado "Aprobado" y cert_uuid
            resultado = str(row_data.get(service.COLUMN_RESULTADO, "")).strip().lower()
            cert_uuid = row_data.get(service.COLUMN_UUID)
            nuevo_email = row_data.get(service.COLUMN_CORREO_ELECTRONICO)
            full_name = row_data.get(service.COLUMN_NOMBRE_COLABORADOR, "Colaborador")
            vencimiento = row_data.get(service.COLUMN_VENCIMIENTO)
            reenviar_check = row_data.get(service.COLUMN_REENVIAR_CORREO)

            logger.info(
                f"Smartsheet webhook: row {row_id} data - "
                f"resultado='{resultado}', cert_uuid='{cert_uuid}', "
                f"email='{nuevo_email}', name='{full_name}', "
                f"reenviar_correo='{reenviar_check}'"
            )

            # Si el trigger fue por "Reenviar correo", solo procesar si está checked
            # (ignorar cuando se desmarca para evitar loop infinito con uncheck)
            triggered_by_reenviar = row_id in reenviar_changed_rows
            if triggered_by_reenviar:
                reenviar_value = str(reenviar_check).strip().lower() if reenviar_check else ""
                if reenviar_value not in ("true", "1", "yes", "sí", "si"):
                    logger.info(
                        f"Smartsheet webhook: row {row_id} 'Reenviar correo' unchecked, skipping"
                    )
                    continue

            if resultado != "aprobado":
                logger.info(
                    f"Smartsheet webhook: row {row_id} resultado='{resultado}', skipping"
                )
                continue

            if not cert_uuid or not str(cert_uuid).strip():
                logger.info(f"Smartsheet webhook: row {row_id} has no cert UUID, skipping")
                continue

            if not nuevo_email or not str(nuevo_email).strip():
                logger.info(f"Smartsheet webhook: row {row_id} email is empty, skipping")
                continue

            # Reenviar certificado al nuevo email
            vencimiento_str = str(vencimiento) if vencimiento else ""
            sent = resend_approved_certificate_email(
                email_to=str(nuevo_email).strip(),
                full_name=str(full_name).strip(),
                cert_uuid=str(cert_uuid).strip(),
                expiration_date_str=vencimiento_str,
            )

            if sent:
                processed += 1
                logger.info(
                    f"Smartsheet webhook: certificado reenviado automaticamente a "
                    f"{nuevo_email} (row {row_id}, UUID {cert_uuid})"
                )
                # Desmarcar "Reenviar correo" para que quede listo para el siguiente uso
                await service.uncheck_reenviar_correo(row_id)
            else:
                logger.error(
                    f"Smartsheet webhook: fallo al reenviar certificado a "
                    f"{nuevo_email} (row {row_id})"
                )

        except Exception as e:
            logger.error(f"Smartsheet webhook: error processing row {row_id}: {str(e)}")

    return {"status": "ok", "processed": processed}


# ──────────────────────────────────────────────
# POST /register  –  Registrar webhook en Smartsheet
# ──────────────────────────────────────────────
@router.post(
    "/register",
    summary="Registrar webhook en Smartsheet",
    description="Crea y habilita un webhook en Smartsheet que apunta al callback URL configurado.",
)
async def register_webhook(api_key: str = Depends(validate_api_key)):
    """
    Registra un nuevo webhook en Smartsheet para la hoja de Registros.
    Smartsheet enviara un challenge al callback URL para verificarlo.
    """
    callback_url = settings.SMARTSHEET_WEBHOOK_CALLBACK_URL
    if not callback_url:
        raise HTTPException(
            status_code=400,
            detail="SMARTSHEET_WEBHOOK_CALLBACK_URL not configured in environment",
        )

    webhook_payload = {
        "name": "Entersys Onboarding - Email Change Detector",
        "callbackUrl": callback_url,
        "scope": "sheet",
        "scopeObjectId": SHEET_REGISTROS_ID,
        "version": 1,
        "events": ["*.*"],
    }

    headers = {
        "Authorization": f"Bearer {settings.SMARTSHEET_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            # Paso 1: Crear el webhook
            resp = await client.post(
                f"{settings.SMARTSHEET_API_BASE_URL}/webhooks",
                json=webhook_payload,
                headers=headers,
            )
            resp.raise_for_status()
            create_result = resp.json()

            webhook_id = create_result.get("result", {}).get("id")
            if not webhook_id:
                logger.error(f"Smartsheet webhook register: no webhook ID in response: {create_result}")
                raise HTTPException(status_code=502, detail="No webhook ID returned by Smartsheet")

            logger.info(f"Smartsheet webhook created with ID {webhook_id}, enabling...")

            # Paso 2: Habilitar el webhook (cambia status a ENABLED)
            enable_resp = await client.put(
                f"{settings.SMARTSHEET_API_BASE_URL}/webhooks/{webhook_id}",
                json={"enabled": True},
                headers=headers,
            )
            enable_resp.raise_for_status()
            enable_result = enable_resp.json()

            logger.info(f"Smartsheet webhook {webhook_id} enabled successfully")

            return {
                "status": "ok",
                "webhook_id": webhook_id,
                "callback_url": callback_url,
                "scope_object_id": SHEET_REGISTROS_ID,
                "enabled": enable_result.get("result", {}).get("enabled", False),
                "message": "Webhook created and enabled. Smartsheet will send a challenge to verify the callback URL.",
            }

    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response else str(e)
        logger.error(f"Smartsheet API error registering webhook: {detail}")
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Network error registering webhook: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Network error: {str(e)}")


# ──────────────────────────────────────────────
# GET /status  –  Estado de webhooks registrados
# ──────────────────────────────────────────────
@router.get(
    "/status",
    summary="Estado de webhooks registrados",
    description="Consulta los webhooks registrados en Smartsheet para esta hoja.",
)
async def webhook_status(api_key: str = Depends(validate_api_key)):
    """Lista los webhooks registrados y su estado."""
    headers = {
        "Authorization": f"Bearer {settings.SMARTSHEET_ACCESS_TOKEN}",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.SMARTSHEET_API_BASE_URL}/webhooks",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        # Filtrar solo los webhooks de nuestra hoja
        all_webhooks = data.get("data", [])
        our_webhooks = [
            wh for wh in all_webhooks
            if wh.get("scopeObjectId") == SHEET_REGISTROS_ID
        ]

        return {
            "status": "ok",
            "total_webhooks": len(all_webhooks),
            "registros_webhooks": len(our_webhooks),
            "webhooks": [
                {
                    "id": wh.get("id"),
                    "name": wh.get("name"),
                    "enabled": wh.get("enabled"),
                    "status": wh.get("status"),
                    "callbackUrl": wh.get("callbackUrl"),
                    "scope": wh.get("scope"),
                    "scopeObjectId": wh.get("scopeObjectId"),
                    "events": wh.get("events"),
                    "version": wh.get("version"),
                }
                for wh in our_webhooks
            ],
        }

    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response else str(e)
        logger.error(f"Smartsheet API error getting webhooks: {detail}")
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Network error getting webhooks: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Network error: {str(e)}")
