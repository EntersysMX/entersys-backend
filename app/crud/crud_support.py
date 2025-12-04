from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.models.support import SupportFAQ, ChatNode, ChatOption
from app.schemas.support import FAQCreate, FAQUpdate, ChatNodeCreate, ChatOptionCreate

class CRUDSupport:
    def get_faqs(
        self, 
        db: Session, 
        role: Optional[str] = None, 
        search_term: Optional[str] = None,
        limit: int = 100
    ) -> List[SupportFAQ]:
        """
        Obtener FAQs filtradas por rol y término de búsqueda.
        """
        query = db.query(SupportFAQ).filter(SupportFAQ.is_active == True)

        # Filtrar por rol (si se especifica)
        if role:
            # Mostrar FAQs para el rol específico O para todos ('ALL')
            query = query.filter(or_(SupportFAQ.target_role == role, SupportFAQ.target_role == 'ALL'))
        
        # Filtrar por búsqueda (si se especifica)
        if search_term:
            search = f"%{search_term}%"
            query = query.filter(
                or_(
                    SupportFAQ.question.ilike(search),
                    SupportFAQ.answer.ilike(search)
                )
            )
        
        # Ordenar por prioridad descendente
        return query.order_by(desc(SupportFAQ.priority)).limit(limit).all()

    def create_faq(self, db: Session, faq: FAQCreate) -> SupportFAQ:
        db_obj = SupportFAQ(**faq.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_chat_flow(self, db: Session) -> Dict[str, Any]:
        """
        Construye el árbol completo del chat en un formato optimizado para el frontend.
        Retorna un diccionario donde las claves son los node_keys.
        """
        nodes = db.query(ChatNode).all()
        
        flow_structure = {}
        
        for node in nodes:
            # Obtener opciones para este nodo
            options_data = []
            for option in node.options:
                options_data.append({
                    "label": option.label,
                    "next_node": option.next_node_key
                })
            
            flow_structure[node.node_key] = {
                "message": node.message_text,
                "type": node.node_type,
                "link": node.external_link,
                "options": options_data
            }
            
        return flow_structure

    def create_chat_node(self, db: Session, node: ChatNodeCreate) -> ChatNode:
        db_obj = ChatNode(**node.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_chat_option(self, db: Session, option: ChatOptionCreate) -> ChatOption:
        db_obj = ChatOption(**option.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

support = CRUDSupport()
