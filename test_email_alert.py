"""
Script de prueba para enviar email de alerta de tercer intento fallido.
Ejecutar: python test_email_alert.py
"""
import sys
import os
sys.path.insert(0, '.')

# Configurar API Key de Resend desde variable de entorno
os.environ['RESEND_API_KEY'] = os.environ.get('RESEND_API_KEY', 're_WWgiBox8_D48pZH258rUi9SBpVJyDez99')

from app.api.v1.endpoints.onboarding import send_third_attempt_alert_email

# Datos de prueba
colaborador_data = {
    "nombre_completo": "Usuario de Prueba",
    "rfc_colaborador": "TEST123456ABC",
    "email": "armando.cortes@entersys.mx",  # Email de prueba
    "proveedor": "Empresa de Prueba S.A.",
    "tipo_servicio": "Mantenimiento",
    "rfc_empresa": "EPR123456ABC",
    "nss": "12345678901",
    "section_results": [
        {"section_number": 1, "section_name": "Seguridad", "correct_count": 6, "total_questions": 10, "score": 60.0, "approved": False},
        {"section_number": 2, "section_name": "Inocuidad", "correct_count": 5, "total_questions": 10, "score": 50.0, "approved": False},
        {"section_number": 3, "section_name": "Ambiental", "correct_count": 7, "total_questions": 10, "score": 70.0, "approved": False}
    ],
    "overall_score": 60.0
}

attempts_info = {
    "total": 3,
    "aprobados": 0,
    "fallidos": 3,
    "registros": []
}

print("Enviando email de prueba de tercer intento fallido...")
print(f"El email de alerta se enviará a los administradores")
print(f"Remitente esperado: Entersys <no-reply@entersys.mx>")

result = send_third_attempt_alert_email(colaborador_data, attempts_info)

if result:
    print("✅ Email enviado exitosamente!")
    print("Revisa tu bandeja de entrada para verificar que llegó desde no-reply@entersys.mx")
else:
    print("❌ Error al enviar el email")
