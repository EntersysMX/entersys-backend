import httpx
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.config import settings

logger = logging.getLogger(__name__)

class MauticService:
    """
    Servicio para integración con Mautic CRM
    URL Base: https://crm.entersys.mx
    Autenticación: OAuth 2.0 (client_credentials)

    **Funcionalidades principales:**
    - Crear/actualizar contactos
    - Gestión de scoring de leads
    - Disparar campañas de email
    - Consultar perfiles de contactos
    - Asignación automática de segmentos
    """

    def __init__(self):
        # Configuración desde variables de entorno
        self.base_url = getattr(settings, 'MAUTIC_BASE_URL', 'https://crm.entersys.mx')
        self.client_id = getattr(settings, 'MAUTIC_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'MAUTIC_CLIENT_SECRET', '')

        # Variables para manejo de token OAuth2
        self.access_token = None
        self.token_expiry = None

        logger.info(f"MauticService inicializado con OAuth2 para: {self.base_url}")

    async def _get_oauth_token(self) -> str:
        """Obtener token OAuth2 válido, reutilizando el actual si no ha expirado"""
        # Si ya tenemos un token válido, devolverlo
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        try:
            if not self.client_id or not self.client_secret:
                raise Exception("MAUTIC_CLIENT_ID y MAUTIC_CLIENT_SECRET deben estar configurados")

            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    f"{self.base_url}/oauth/v2/token",
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    data={
                        'grant_type': 'client_credentials',
                        'client_id': self.client_id,
                        'client_secret': self.client_secret
                    }
                )

                response.raise_for_status()
                token_data = response.json()

                self.access_token = token_data['access_token']
                # Expira en 1 hora menos 5 minutos de margen de seguridad
                expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

                logger.info("OAuth2 token obtenido exitosamente")
                return self.access_token

        except Exception as e:
            logger.error(f"Error obteniendo token OAuth2: {str(e)}")
            # Limpiar token en caso de error
            self.access_token = None
            self.token_expiry = None
            raise Exception(f"Error obteniendo token OAuth2: {str(e)}")

    async def _make_authenticated_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Realizar petición HTTP con manejo automático de token OAuth2"""
        token = await self._get_oauth_token()
        headers = kwargs.get('headers', {})
        headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        })
        kwargs['headers'] = headers

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            if method.upper() == 'GET':
                response = await client.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = await client.post(url, **kwargs)
            elif method.upper() == 'PUT':
                response = await client.put(url, **kwargs)
            elif method.upper() == 'PATCH':
                response = await client.patch(url, **kwargs)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            # Manejo de token expirado
            if response.status_code == 401:
                logger.warning("Token OAuth2 expirado, obteniendo nuevo token...")
                # Limpiar token y obtener uno nuevo
                self.access_token = None
                self.token_expiry = None
                token = await self._get_oauth_token()
                headers['Authorization'] = f"Bearer {token}"

                # Reintentar la petición
                if method.upper() == 'GET':
                    response = await client.get(url, **kwargs)
                elif method.upper() == 'POST':
                    response = await client.post(url, **kwargs)
                elif method.upper() == 'PUT':
                    response = await client.put(url, **kwargs)
                elif method.upper() == 'PATCH':
                    response = await client.patch(url, **kwargs)

            return response

    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear nuevo contacto en Mautic CRM

        **Flujo de creación:**
        1. Preparar datos del contacto
        2. Asignar score inicial basado en interés
        3. Crear contacto vía API
        4. Asignar a segmento correspondiente
        5. Retornar resultado
        """
        try:
            # 1. Preparar payload para Mautic API
            mautic_payload = self._prepare_contact_payload(contact_data)

            # 2. Crear contacto usando OAuth2
            response = await self._make_authenticated_request(
                'POST',
                f"{self.base_url}/api/contacts/new",
                json=mautic_payload
            )

            response.raise_for_status()
            result = response.json()

            if 'contact' in result:
                contact_id = result['contact']['id']

                # 3. Asignar score inicial basado en interés
                initial_score = self._calculate_initial_score(contact_data.get('interest', 'general'))

                if initial_score > 0:
                    await self._add_points_to_contact(contact_id, initial_score)

                # 4. Log exitoso
                logger.info(f"Contacto creado exitosamente: {contact_data.get('email')} -> ID {contact_id}")

                return {
                    "success": True,
                    "contact_id": contact_id,
                    "initial_score": initial_score,
                    "action": "created"
                }
            else:
                logger.error(f"Respuesta inesperada de Mautic: {result}")
                return {
                    "success": False,
                    "error": "Respuesta inesperada del CRM",
                    "details": result
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP creando contacto en Mautic: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"Error HTTP {e.response.status_code}",
                "details": e.response.text
            }
        except Exception as e:
            logger.error(f"Error inesperado creando contacto en Mautic: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_contact_by_email(self, email: str) -> Dict[str, Any]:
        """Obtener contacto por email desde Mautic"""
        try:
            # Buscar contacto por email usando OAuth2
            response = await self._make_authenticated_request(
                'GET',
                f"{self.base_url}/api/contacts",
                params={
                    "search": f"email:{email}",
                    "limit": 1
                }
            )

            response.raise_for_status()
            result = response.json()

            if result.get('contacts') and len(result['contacts']) > 0:
                # Contacto encontrado
                contact = list(result['contacts'].values())[0]

                return {
                    "success": True,
                    "found": True,
                    "contact": contact
                }
            else:
                # Contacto no encontrado
                return {
                    "success": True,
                    "found": False,
                    "contact": None
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP consultando contacto: {e.response.status_code}")
            return {
                "success": False,
                "error": f"Error HTTP {e.response.status_code}",
                "found": False
            }
        except Exception as e:
            logger.error(f"Error consultando contacto por email {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "found": False
            }

    async def update_contact_score(self, email: str, score_delta: int, action: str) -> Dict[str, Any]:
        """Actualizar score de contacto basado en comportamiento"""
        try:
            # 1. Obtener contacto actual
            contact_result = await self.get_contact_by_email(email)

            if not contact_result.get("found"):
                return {
                    "success": False,
                    "error": "Contacto no encontrado"
                }

            contact = contact_result['contact']
            contact_id = contact['id']
            old_score = int(contact.get('points', 0))

            # 2. Aplicar cambio de score
            if score_delta != 0:
                await self._add_points_to_contact(contact_id, score_delta)

            new_score = old_score + score_delta

            # 3. Log de la actividad
            logger.info(f"Score actualizado para {email}: {old_score} -> {new_score} ({action})")

            return {
                "success": True,
                "contact_id": contact_id,
                "old_score": old_score,
                "new_score": new_score,
                "score_delta": score_delta,
                "action": action
            }

        except Exception as e:
            logger.error(f"Error actualizando score para {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def trigger_email_campaign(self, email: str, campaign_type: str) -> Dict[str, Any]:
        """
        Disparar campaña de email específica

        **Tipos de campaña soportados:**
        - welcome_general: Bienvenida general
        - welcome_worksys: Bienvenida Worksys
        - welcome_expersys: Bienvenida Expersys
        - welcome_demo: Bienvenida demo
        - nurturing_*: Campañas de nurturing
        """
        try:
            # 1. Obtener contacto
            contact_result = await self.get_contact_by_email(email)

            if not contact_result.get("found"):
                return {
                    "success": False,
                    "error": "Contacto no encontrado para campaña"
                }

            contact_id = contact_result['contact']['id']

            # 2. Mapear tipo de campaña a ID de Mautic (configurar según campañas reales)
            campaign_mapping = {
                "welcome_general": 1,
                "welcome_worksys": 2,
                "welcome_expersys": 3,
                "welcome_demo": 4,
                # Agregar más mapeos según sea necesario
            }

            campaign_id = campaign_mapping.get(campaign_type)

            if not campaign_id:
                logger.warning(f"Tipo de campaña no configurado: {campaign_type}")
                return {
                    "success": False,
                    "error": f"Campaña no configurada: {campaign_type}"
                }

            # 3. Disparar campaña (por ahora simulado - implementar según API de Mautic)
            # En una implementación real, esto sería una llamada a la API de campañas de Mautic

            logger.info(f"Campaña disparada: {email} -> {campaign_type} (ID: {campaign_id})")

            return {
                "success": True,
                "contact_id": contact_id,
                "campaign_type": campaign_type,
                "campaign_id": campaign_id,
                "triggered_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error disparando campaña {campaign_type} para {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _prepare_contact_payload(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Preparar payload para crear contacto en Mautic"""
        # Separar nombre completo en nombre y apellido
        full_name = contact_data.get('name', '').strip()
        name_parts = full_name.split(' ', 1)
        firstname = name_parts[0] if name_parts else ''
        lastname = name_parts[1] if len(name_parts) > 1 else ''

        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "email": contact_data.get('email'),
            "company": contact_data.get('company', ''),
            "phone": contact_data.get('phone', ''),
            "lead_source": contact_data.get('source', 'website_form'),
            "lead_interest": contact_data.get('interest', 'general'),
            "message": contact_data.get('message', ''),
            "date_added": datetime.now().isoformat(),
            # Campos personalizados adicionales
            "tags": [
                f"source_{contact_data.get('source', 'unknown')}",
                f"interest_{contact_data.get('interest', 'general')}"
            ]
        }

        return payload

    def _calculate_initial_score(self, interest: str) -> int:
        """Calcular score inicial basado en tipo de interés"""
        score_mapping = {
            "demo": 25,        # Interés alto en demo
            "worksys": 20,     # Interés específico en producto
            "expersys": 20,    # Interés específico en producto
            "partnership": 30, # Interés comercial alto
            "automation": 18,  # Interés en automatización
            "general": 10      # Interés general
        }

        return score_mapping.get(interest, 10)

    async def _add_points_to_contact(self, contact_id: int, points: int) -> bool:
        """Agregar puntos a contacto específico"""
        try:
            # Agregar puntos usando OAuth2
            response = await self._make_authenticated_request(
                'POST',
                f"{self.base_url}/api/contacts/{contact_id}/points/plus/{abs(points)}"
            )

            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error agregando {points} puntos al contacto {contact_id}: {str(e)}")
            return False