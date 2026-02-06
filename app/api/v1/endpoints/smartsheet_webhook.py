# app/api/v1/endpoints/smartsheet_webhook.py
from fastapi import APIRouter, Header, Depends, HTTPException, Request, status, BackgroundTasks
from typing import Optional, List, Dict, Any
import logging
import httpx
import asyncio
from datetime import datetime

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

# Cola en memoria para tracking de jobs (para consultar estado)
_processing_jobs: Dict[str, Dict[str, Any]] = {}


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


async def process_email_queue(job_id: str, row_ids: List[int]):
    """
    Procesa una cola de filas para reenvío de certificados en background.

    - Procesa cada fila con delay de 3 segundos entre envíos
    - Reintenta hasta 3 veces si falla un envío
    - Actualiza el estado del job para consultas
    """
    job = _processing_jobs.get(job_id, {})
    job["status"] = "processing"
    job["started_at"] = datetime.utcnow().isoformat()
    job["total"] = len(row_ids)
    job["processed"] = 0
    job["success"] = 0
    job["failed"] = 0
    job["skipped"] = 0
    job["details"] = []
    _processing_jobs[job_id] = job

    logger.info(f"Background job {job_id}: Starting to process {len(row_ids)} rows")

    service = get_onboarding_service()
    await service._get_registros_column_maps()

    for row_id in row_ids:
        result = {"row_id": row_id, "status": "pending", "email": None, "error": None}

        try:
            row_data = await service.get_row_data_by_id(row_id)
            if row_data is None:
                result["status"] = "skipped"
                result["error"] = "could not read row"
                job["skipped"] += 1
                job["details"].append(result)
                job["processed"] += 1
                continue

            # Extraer datos
            resultado = str(row_data.get(service.COLUMN_RESULTADO, "")).strip().lower()
            cert_uuid = row_data.get(service.COLUMN_UUID)
            nuevo_email = row_data.get(service.COLUMN_CORREO_ELECTRONICO)
            full_name = row_data.get(service.COLUMN_NOMBRE_COLABORADOR, "Colaborador")
            vencimiento = row_data.get(service.COLUMN_VENCIMIENTO)
            reenviar_check = row_data.get(service.COLUMN_REENVIAR_CORREO)

            result["email"] = nuevo_email
            result["name"] = full_name

            # Verificar que "Reenviar correo" esté activo
            reenviar_value = str(reenviar_check).strip().lower() if reenviar_check else ""
            if reenviar_value not in ("true", "1", "yes", "sí", "si"):
                result["status"] = "skipped"
                result["error"] = "checkbox not checked"
                job["skipped"] += 1
                job["details"].append(result)
                job["processed"] += 1
                continue

            if resultado != "aprobado":
                result["status"] = "skipped"
                result["error"] = f"resultado={resultado}"
                job["skipped"] += 1
                job["details"].append(result)
                job["processed"] += 1
                continue

            if not cert_uuid or not str(cert_uuid).strip():
                result["status"] = "skipped"
                result["error"] = "no cert UUID"
                job["skipped"] += 1
                job["details"].append(result)
                job["processed"] += 1
                continue

            if not nuevo_email or not str(nuevo_email).strip():
                result["status"] = "skipped"
                result["error"] = "empty email"
                job["skipped"] += 1
                job["details"].append(result)
                job["processed"] += 1
                continue

            # Extraer datos del colaborador para el PDF
            collaborator_data = {
                "nombre_completo": str(full_name).strip(),
                "rfc_colaborador": row_data.get(service.COLUMN_RFC_COLABORADOR, ""),
                "rfc_empresa": row_data.get(service.COLUMN_RFC_EMPRESA, ""),
                "nss": row_data.get(service.COLUMN_NSS_COLABORADOR, ""),
                "tipo_servicio": row_data.get(service.COLUMN_TIPO_SERVICIO, ""),
                "proveedor": row_data.get(service.COLUMN_PROVEEDOR_EMPRESA, ""),
                "foto_url": row_data.get(service.COLUMN_URL_IMAGEN, ""),
            }

            section_results = {
                "Seguridad": row_data.get(service.COLUMN_SECCION1, 0),
                "Inocuidad": row_data.get(service.COLUMN_SECCION2, 0),
                "Ambiental": row_data.get(service.COLUMN_SECCION3, 0),
            }

            # Enviar con reintentos
            vencimiento_str = str(vencimiento) if vencimiento else ""
            max_retries = 3
            sent = False

            for attempt in range(max_retries):
                try:
                    sent = resend_approved_certificate_email(
                        email_to=str(nuevo_email).strip(),
                        full_name=str(full_name).strip(),
                        cert_uuid=str(cert_uuid).strip(),
                        expiration_date_str=vencimiento_str,
                        collaborator_data=collaborator_data,
                        section_results=section_results,
                    )
                    if sent:
                        break
                except Exception as send_error:
                    logger.warning(f"Job {job_id}: Attempt {attempt+1} failed for {nuevo_email}: {send_error}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)  # Esperar antes de reintentar

            if sent:
                result["status"] = "success"
                job["success"] += 1
                logger.info(f"Job {job_id}: Email sent to {nuevo_email}")
                # Desmarcar checkbox
                try:
                    await service.uncheck_reenviar_correo(row_id)
                except Exception as uncheck_error:
                    logger.warning(f"Job {job_id}: Could not uncheck row {row_id}: {uncheck_error}")
            else:
                result["status"] = "failed"
                result["error"] = "send failed after retries"
                job["failed"] += 1
                logger.error(f"Job {job_id}: Failed to send to {nuevo_email}")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            job["failed"] += 1
            logger.error(f"Job {job_id}: Error processing row {row_id}: {e}")

        job["details"].append(result)
        job["processed"] += 1

        # Delay entre envíos (3 segundos)
        await asyncio.sleep(3)

    job["status"] = "completed"
    job["completed_at"] = datetime.utcnow().isoformat()
    logger.info(
        f"Background job {job_id}: Completed - "
        f"success={job['success']}, failed={job['failed']}, skipped={job['skipped']}"
    )

    # Limpiar jobs viejos (mantener últimos 50)
    if len(_processing_jobs) > 50:
        oldest_keys = sorted(_processing_jobs.keys())[:-50]
        for key in oldest_keys:
            del _processing_jobs[key]


# ──────────────────────────────────────────────
# POST /callback  –  Webhook callback de Smartsheet
# ──────────────────────────────────────────────
@router.post(
    "/callback",
    summary="Callback del webhook de Smartsheet",
    description="Recibe notificaciones de cambios en la hoja de Registros. "
    "Detecta cambios en la columna 'Reenviar correo' y encola "
    "el reenvío de certificados en background.",
)
async def webhook_callback(request: Request, background_tasks: BackgroundTasks):
    """
    Callback que Smartsheet invoca cuando hay cambios en la hoja.

    El procesamiento se hace en background para evitar timeouts.
    Responde inmediatamente con un job_id para consultar el estado.
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

    # Validar que el evento sea de la hoja correcta
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

    # ── Obtener column IDs ──
    service = get_onboarding_service()
    await service._get_registros_column_maps()
    reenviar_column_id = service.get_reenviar_correo_column_id()

    if not reenviar_column_id:
        logger.error("Smartsheet webhook: could not resolve 'Reenviar correo' column ID")
        return {"status": "error", "reason": "column_id_not_found"}

    # ── Filtrar eventos: solo cambios en "Reenviar correo" ──
    affected_row_ids = set()
    for event in events:
        if event.get("objectType") != "cell" or event.get("eventType") != "updated":
            continue
        if event.get("columnId") == reenviar_column_id:
            affected_row_ids.add(event["rowId"])

    if not affected_row_ids:
        logger.debug("Smartsheet webhook: no 'Reenviar correo' changes detected")
        return {"status": "ok", "queued": 0}

    # ── Crear job y encolar en background ──
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(affected_row_ids)}"
    rows_list = list(affected_row_ids)

    _processing_jobs[job_id] = {
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "total": len(rows_list),
        "row_ids": rows_list,
    }

    # Encolar procesamiento en background
    background_tasks.add_task(process_email_queue, job_id, rows_list)

    logger.info(
        f"Smartsheet webhook: Queued {len(rows_list)} rows for processing (job_id={job_id})"
    )

    return {
        "status": "queued",
        "job_id": job_id,
        "queued_rows": len(rows_list),
        "message": f"Processing {len(rows_list)} rows in background. Check /job-status/{job_id} for progress."
    }


# ──────────────────────────────────────────────
# GET /job-status/{job_id}  –  Estado de un job
# ──────────────────────────────────────────────
@router.get(
    "/job-status/{job_id}",
    summary="Estado de un job de procesamiento",
    description="Consulta el estado y progreso de un job de reenvío de certificados.",
)
async def get_job_status(job_id: str):
    """Retorna el estado actual de un job de procesamiento."""
    job = _processing_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # No incluir detalles completos si hay muchos
    response = {k: v for k, v in job.items() if k != "details"}
    if job.get("details"):
        response["details_count"] = len(job["details"])
        # Solo mostrar últimos 10 detalles
        response["recent_details"] = job["details"][-10:]

    return response


# ──────────────────────────────────────────────
# GET /jobs  –  Lista de jobs recientes
# ──────────────────────────────────────────────
@router.get(
    "/jobs",
    summary="Lista de jobs de procesamiento",
    description="Lista los jobs de reenvío de certificados recientes.",
)
async def list_jobs(api_key: str = Depends(validate_api_key)):
    """Lista todos los jobs de procesamiento recientes."""
    jobs_summary = []
    for job_id, job in sorted(_processing_jobs.items(), reverse=True):
        jobs_summary.append({
            "job_id": job_id,
            "status": job.get("status"),
            "total": job.get("total"),
            "processed": job.get("processed", 0),
            "success": job.get("success", 0),
            "failed": job.get("failed", 0),
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
        })
    return {"jobs": jobs_summary[:20]}  # Últimos 20 jobs


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
                "message": "Webhook created and enabled.",
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
