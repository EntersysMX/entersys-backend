# app/services/onboarding_smartsheet_service.py
import smartsheet
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from app.core.config import settings


class OnboardingSmartsheetServiceError(Exception):
    """Excepción personalizada para errores del servicio de Smartsheet de Onboarding"""
    pass


class OnboardingSmartsheetService:
    """
    Servicio especializado para operaciones de Smartsheet relacionadas con el
    sistema de validación de onboarding dinámico.
    """

    # Nombres de columnas en Smartsheet (ajustar según la hoja real)
    COLUMN_CERT_UUID = "CERT_UUID"
    COLUMN_EXPIRATION = "Vencimiento"
    COLUMN_QR_SENT = "QR Enviado"
    COLUMN_LAST_VALIDATION = "Última Validación"
    COLUMN_FULL_NAME = "Nombre Completo"
    COLUMN_EMAIL = "Email"
    COLUMN_SCORE = "Score"
    COLUMN_CERT_VALID = "Certificado Válido"

    def __init__(self, sheet_id: Optional[int] = None):
        """
        Inicializa el servicio de Smartsheet para Onboarding.

        Args:
            sheet_id: ID de la hoja de Smartsheet (opcional, puede usar SHEET_ID del env)
        """
        self.logger = logging.getLogger(__name__)
        self.sheet_id = sheet_id

        try:
            self.client = smartsheet.Smartsheet(settings.SMARTSHEET_ACCESS_TOKEN)
            self.client.errors_as_exceptions(True)
            self.logger.info("Onboarding Smartsheet service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Smartsheet client: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Error initializing Smartsheet client: {str(e)}"
            )

        # Cache de mapeo columna ID -> nombre
        self._column_map: Dict[int, str] = {}
        self._reverse_column_map: Dict[str, int] = {}

    async def _get_column_maps(self, sheet_id: int) -> None:
        """
        Obtiene y cachea el mapeo de columnas para una hoja.

        Args:
            sheet_id: ID de la hoja
        """
        if self._column_map:
            return

        try:
            sheet = self.client.Sheets.get_sheet(sheet_id, include=['format'])

            for column in sheet.columns:
                self._column_map[column.id] = column.title
                self._reverse_column_map[column.title] = column.id

            self.logger.debug(f"Loaded {len(self._column_map)} columns for sheet {sheet_id}")

        except Exception as e:
            self.logger.error(f"Error loading column maps: {str(e)}")
            raise OnboardingSmartsheetServiceError(f"Error loading column maps: {str(e)}")

    def _get_column_id(self, column_name: str) -> int:
        """
        Obtiene el ID de una columna por su nombre.

        Args:
            column_name: Nombre de la columna

        Returns:
            ID de la columna

        Raises:
            OnboardingSmartsheetServiceError: Si la columna no existe
        """
        if column_name not in self._reverse_column_map:
            raise OnboardingSmartsheetServiceError(
                f"Column '{column_name}' not found in sheet"
            )
        return self._reverse_column_map[column_name]

    async def update_row_with_certificate(
        self,
        sheet_id: int,
        row_id: int,
        cert_uuid: str,
        expiration_date: datetime,
        is_valid: bool = True,
        score: float = 0.0
    ) -> bool:
        """
        Actualiza una fila de Smartsheet con los datos del certificado generado.

        Args:
            sheet_id: ID de la hoja
            row_id: ID de la fila a actualizar
            cert_uuid: UUID del certificado generado
            expiration_date: Fecha de vencimiento del certificado
            is_valid: Si el certificado es válido (score >= 80)
            score: Puntuación obtenida

        Returns:
            True si la actualización fue exitosa
        """
        try:
            await self._get_column_maps(sheet_id)

            # Construir las celdas a actualizar
            cells = [
                {
                    'column_id': self._get_column_id(self.COLUMN_CERT_UUID),
                    'value': cert_uuid
                },
                {
                    'column_id': self._get_column_id(self.COLUMN_EXPIRATION),
                    'value': expiration_date.strftime('%Y-%m-%d')
                },
                {
                    'column_id': self._get_column_id(self.COLUMN_QR_SENT),
                    'value': True
                }
            ]

            # Agregar columna de validez si existe
            try:
                cells.append({
                    'column_id': self._get_column_id(self.COLUMN_CERT_VALID),
                    'value': is_valid
                })
            except OnboardingSmartsheetServiceError:
                self.logger.warning(f"Column '{self.COLUMN_CERT_VALID}' not found, skipping")

            # Crear objeto de fila para actualización
            row_to_update = smartsheet.models.Row()
            row_to_update.id = row_id
            row_to_update.cells = [
                smartsheet.models.Cell(cell) for cell in cells
            ]

            # Ejecutar actualización
            response = self.client.Sheets.update_rows(sheet_id, [row_to_update])

            if response.message == 'SUCCESS':
                self.logger.info(
                    f"Successfully updated row {row_id} with certificate {cert_uuid}"
                )
                return True
            else:
                self.logger.error(f"Unexpected response updating row: {response.message}")
                return False

        except smartsheet.exceptions.ApiError as e:
            self.logger.error(f"Smartsheet API error updating row: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Smartsheet API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error updating row with certificate: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Error updating row: {str(e)}"
            )

    async def update_last_validation(
        self,
        sheet_id: int,
        row_id: int,
        validation_time: Optional[datetime] = None
    ) -> bool:
        """
        Actualiza la columna 'Última Validación' de una fila.

        Args:
            sheet_id: ID de la hoja
            row_id: ID de la fila
            validation_time: Hora de validación (usa ahora si no se especifica)

        Returns:
            True si la actualización fue exitosa
        """
        try:
            await self._get_column_maps(sheet_id)

            if validation_time is None:
                validation_time = datetime.utcnow()

            # Construir celda a actualizar
            cell = smartsheet.models.Cell()
            cell.column_id = self._get_column_id(self.COLUMN_LAST_VALIDATION)
            cell.value = validation_time.strftime('%Y-%m-%d %H:%M:%S')

            # Crear fila para actualización
            row_to_update = smartsheet.models.Row()
            row_to_update.id = row_id
            row_to_update.cells = [cell]

            # Ejecutar actualización
            response = self.client.Sheets.update_rows(sheet_id, [row_to_update])

            if response.message == 'SUCCESS':
                self.logger.info(
                    f"Updated last validation for row {row_id} to {validation_time}"
                )
                return True
            else:
                self.logger.error(f"Unexpected response: {response.message}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating last validation: {str(e)}")
            # No re-raise para que la tarea en background no falle silenciosamente
            return False

    async def get_certificate_by_uuid(
        self,
        sheet_id: int,
        cert_uuid: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca un certificado por su UUID en Smartsheet.

        Args:
            sheet_id: ID de la hoja
            cert_uuid: UUID del certificado a buscar

        Returns:
            Diccionario con los datos del certificado o None si no existe
        """
        try:
            await self._get_column_maps(sheet_id)

            # Obtener la hoja completa
            sheet = self.client.Sheets.get_sheet(sheet_id)

            # Buscar la fila con el UUID
            for row in sheet.rows:
                row_data = {}

                for cell in row.cells:
                    column_name = self._column_map.get(cell.column_id, f"Col_{cell.column_id}")
                    cell_value = cell.display_value if cell.display_value is not None else cell.value
                    row_data[column_name] = cell_value

                # Verificar si es el UUID buscado
                if row_data.get(self.COLUMN_CERT_UUID) == cert_uuid:
                    row_data['row_id'] = row.id
                    self.logger.info(f"Found certificate {cert_uuid} in row {row.id}")
                    return row_data

            self.logger.warning(f"Certificate {cert_uuid} not found in sheet {sheet_id}")
            return None

        except smartsheet.exceptions.ApiError as e:
            self.logger.error(f"Smartsheet API error searching for certificate: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Smartsheet API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error searching for certificate: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Error searching for certificate: {str(e)}"
            )

    def is_certificate_valid(self, certificate_data: Dict[str, Any]) -> bool:
        """
        Verifica si un certificado es válido (score >= 80 y no expirado).

        Args:
            certificate_data: Datos del certificado de Smartsheet

        Returns:
            True si el certificado es válido
        """
        try:
            # Verificar el score directamente
            score_value = certificate_data.get(self.COLUMN_SCORE)
            if score_value is not None:
                try:
                    score = float(str(score_value).replace('%', '').strip())
                    if score < 80.0:
                        self.logger.info(f"Certificate invalid: score {score} < 80")
                        return False
                except (ValueError, TypeError):
                    self.logger.warning(f"Could not parse score value: {score_value}")

            # También verificar columna de validez si existe
            cert_valid = certificate_data.get(self.COLUMN_CERT_VALID)
            if cert_valid is not None and str(cert_valid).lower() in ['false', '0', 'no']:
                self.logger.info("Certificate marked as invalid (score < 80)")
                return False

            expiration_str = certificate_data.get(self.COLUMN_EXPIRATION)

            if not expiration_str:
                self.logger.warning("Certificate has no expiration date")
                return False

            # Parsear fecha de vencimiento (puede venir en varios formatos)
            expiration_date = None
            for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    expiration_date = datetime.strptime(str(expiration_str), date_format)
                    break
                except ValueError:
                    continue

            if expiration_date is None:
                self.logger.error(f"Could not parse expiration date: {expiration_str}")
                return False

            # Verificar si está expirado
            is_valid = expiration_date.date() >= datetime.utcnow().date()

            if not is_valid:
                self.logger.info(
                    f"Certificate expired on {expiration_date.date()}"
                )

            return is_valid

        except Exception as e:
            self.logger.error(f"Error validating certificate: {str(e)}")
            return False

    async def get_attempts_by_rfc(
        self,
        sheet_id: int,
        rfc_colaborador: str
    ) -> Dict[str, Any]:
        """
        Cuenta los intentos aprobados y fallidos de un colaborador por su RFC.

        Args:
            sheet_id: ID de la hoja
            rfc_colaborador: RFC del colaborador a buscar

        Returns:
            Diccionario con conteo de intentos:
            {
                "total": int,
                "aprobados": int,
                "fallidos": int,
                "registros": List[Dict] - Lista con datos de cada intento
            }
        """
        try:
            await self._get_column_maps(sheet_id)

            # Obtener la hoja completa
            sheet = self.client.Sheets.get_sheet(sheet_id)

            # Contadores
            total = 0
            aprobados = 0
            fallidos = 0
            registros = []

            # Buscar todas las filas con el mismo RFC
            for row in sheet.rows:
                row_data = {}

                for cell in row.cells:
                    column_name = self._column_map.get(cell.column_id, f"Col_{cell.column_id}")
                    cell_value = cell.display_value if cell.display_value is not None else cell.value
                    row_data[column_name] = cell_value

                # Verificar si es el RFC buscado
                rfc_value = row_data.get("RFC Colaborador", "")
                if rfc_value and str(rfc_value).strip().upper() == str(rfc_colaborador).strip().upper():
                    total += 1
                    row_data['row_id'] = row.id

                    # Verificar estado (aprobado o no)
                    estado = row_data.get("Estado", "")
                    score_value = row_data.get("Score", 0)

                    # Determinar si aprobó por score o estado
                    is_approved = False
                    if estado:
                        is_approved = str(estado).lower() in ["aprobado", "approved"]
                    elif score_value:
                        try:
                            score = float(str(score_value).replace('%', '').strip())
                            is_approved = score >= 80.0
                        except (ValueError, TypeError):
                            pass

                    if is_approved:
                        aprobados += 1
                    else:
                        fallidos += 1

                    registros.append({
                        "row_id": row.id,
                        "nombre": row_data.get("Nombre Completo", ""),
                        "email": row_data.get("Email", ""),
                        "score": row_data.get("Score", ""),
                        "estado": estado,
                        "is_approved": is_approved
                    })

            self.logger.info(
                f"RFC {rfc_colaborador}: {total} intentos totales, "
                f"{aprobados} aprobados, {fallidos} fallidos"
            )

            return {
                "total": total,
                "aprobados": aprobados,
                "fallidos": fallidos,
                "registros": registros
            }

        except smartsheet.exceptions.ApiError as e:
            self.logger.error(f"Smartsheet API error getting attempts by RFC: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Smartsheet API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error getting attempts by RFC: {str(e)}")
            raise OnboardingSmartsheetServiceError(
                f"Error getting attempts by RFC: {str(e)}"
            )

    async def health_check(self) -> Dict[str, Any]:
        """
        Verifica que el servicio de Smartsheet esté funcionando.

        Returns:
            Diccionario con el estado del servicio
        """
        try:
            user_info = self.client.Users.get_current_user()

            return {
                "status": "healthy",
                "user": user_info.email if hasattr(user_info, 'email') else "unknown",
                "service": "onboarding_smartsheet",
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "onboarding_smartsheet",
                "timestamp": datetime.utcnow().isoformat()
            }
