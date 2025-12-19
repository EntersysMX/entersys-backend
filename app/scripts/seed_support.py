from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.support import ChatNode, ChatOption, SupportFAQ

def seed_data():
    db = SessionLocal()
    try:
        # --- Limpiar datos existentes ---
        db.query(ChatOption).delete()
        db.query(ChatNode).delete()
        db.query(SupportFAQ).delete()
        db.commit()

        print("Datos anteriores eliminados.")

        # --- Crear Nodos del Chatbot ---
        
        # Nodo Inicial
        start_node = ChatNode(
            node_key="start",
            message_text="¡Hola! Soy el asistente virtual de Entersys. ¿En qué puedo ayudarte hoy?",
            node_type="MENU"
        )
        db.add(start_node)

        # Nodo Menú KOF
        kof_menu = ChatNode(
            node_key="menu_kof",
            message_text="Selecciona una opción para KOF:",
            node_type="MENU"
        )
        db.add(kof_menu)

        # Nodo Menú Contratistas
        contractor_menu = ChatNode(
            node_key="menu_contractor",
            message_text="Selecciona una opción para Contratistas:",
            node_type="MENU"
        )
        db.add(contractor_menu)

        # Nodos Finales
        vpn_help = ChatNode(
            node_key="vpn_help",
            message_text="Para problemas de VPN, por favor contacta a la mesa de ayuda al 55-1234-5678 opción 2.",
            node_type="FINAL_TEXT"
        )
        db.add(vpn_help)

        wiki_link = ChatNode(
            node_key="wiki_link",
            message_text="Te redirigiré a nuestra Wiki con la documentación completa.",
            node_type="FINAL_LINK",
            external_link="https://wiki.entersys.mx"
        )
        db.add(wiki_link)

        db.commit()

        # --- Crear Opciones ---
        
        # Opciones para Start
        op1 = ChatOption(parent_node_key="start", label="Soy KOF", next_node_key="menu_kof")
        op2 = ChatOption(parent_node_key="start", label="Soy Contratista", next_node_key="menu_contractor")
        db.add_all([op1, op2])

        # Opciones para KOF
        op3 = ChatOption(parent_node_key="menu_kof", label="Problemas de VPN", next_node_key="vpn_help")
        op4 = ChatOption(parent_node_key="menu_kof", label="Documentación", next_node_key="wiki_link")
        db.add_all([op3, op4])

        # Opciones para Contratistas
        op5 = ChatOption(parent_node_key="menu_contractor", label="Acceso a Planta", next_node_key="wiki_link")
        db.add(op5)

        db.commit()
        print("Nodos y Opciones creados exitosamente.")

        # --- Crear FAQs ---
        # FAQs Generales (ALL)
        faq1 = SupportFAQ(
            question="¿Cómo restablezco mi contraseña?",
            answer="Para restablecer tu contraseña, ve a la página de inicio de sesión y haz clic en 'Olvidé mi contraseña'.",
            category="ACCESO",
            target_role="ALL",
            priority=10
        )
        
        # FAQs para KOF
        faq2 = SupportFAQ(
            question="¿Cuál es la URL de la VPN?",
            answer="La URL de la VPN para KOF es vpn.kof.com.mx",
            category="CONECTIVIDAD",
            target_role="KOF",
            priority=5
        )
        faq_kof_1 = SupportFAQ(
            question="¿Cómo solicito permisos de acceso a sistemas?",
            answer="Los permisos de acceso a sistemas se solicitan a través del portal de TI en la sección 'Solicitudes'. Tu jefe directo debe aprobar la solicitud.",
            category="ACCESO",
            target_role="KOF",
            priority=7
        )
        faq_kof_2 = SupportFAQ(
            question="¿Dónde encuentro los manuales de procedimientos?",
            answer="Todos los manuales de procedimientos están disponibles en nuestra Wiki: https://wiki.entersys.mx",
            category="DOCUMENTACIÓN",
            target_role="KOF",
            priority=6
        )
        faq_kof_3 = SupportFAQ(
            question="¿A quién contacto para problemas de red?",
            answer="Para problemas de red o conectividad, contacta a la mesa de ayuda al 55-1234-5678 opción 2 o envía un ticket a soporte@entersys.mx",
            category="CONECTIVIDAD",
            target_role="KOF",
            priority=8
        )
        
        # FAQs para CONTRACTOR
        faq3 = SupportFAQ(
            question="¿Qué documentos necesito para ingresar?",
            answer="Necesitas tu DC3, IMSS vigente y credencial de elector.",
            category="ACCESO",
            target_role="CONTRACTOR",
            priority=8
        )
        faq_cont_1 = SupportFAQ(
            question="¿Cómo solicito acceso a la planta?",
            answer="El acceso a la planta se solicita a través de tu supervisor. Debes presentar: DC3 vigente, IMSS actualizado, examen médico y constancia de inducción de seguridad.",
            category="ACCESO",
            target_role="CONTRACTOR",
            priority=9
        )
        faq_cont_2 = SupportFAQ(
            question="¿Dónde entrego mi documentación?",
            answer="La documentación se entrega en el área de Recursos Humanos de planta, en horario de 8:00 a 14:00 hrs de lunes a viernes.",
            category="ADMINISTRATIVO",
            target_role="CONTRACTOR",
            priority=7
        )
        faq_cont_3 = SupportFAQ(
            question="¿Qué equipo de seguridad necesito?",
            answer="El equipo de protección personal obligatorio incluye: casco, lentes de seguridad, zapatos de seguridad, y chaleco reflejante. Tu empresa debe proporcionártelo.",
            category="SEGURIDAD",
            target_role="CONTRACTOR",
            priority=10
        )
        faq_cont_4 = SupportFAQ(
            question="¿Cómo reporto un incidente de seguridad?",
            answer="Los incidentes de seguridad deben reportarse inmediatamente a tu supervisor y al coordinador de QHSE. También puedes llamar al 55-1234-5678 opción 3.",
            category="SEGURIDAD",
            target_role="CONTRACTOR",
            priority=10
        )
        faq_cont_5 = SupportFAQ(
            question="¿Cuál es el horario de trabajo?",
            answer="El horario de trabajo para contratistas varía según el proyecto. Consulta con tu supervisor para conocer tu horario específico.",
            category="ADMINISTRATIVO",
            target_role="CONTRACTOR",
            priority=5
        )
        
        db.add_all([faq1, faq2, faq3, faq_kof_1, faq_kof_2, faq_kof_3, faq_cont_1, faq_cont_2, faq_cont_3, faq_cont_4, faq_cont_5])
        db.commit()
        print("FAQs creadas exitosamente.")

    except Exception as e:
        print(f"Error al poblar datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
