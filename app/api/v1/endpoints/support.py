from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.support import FAQ, ChatFlowResponse
from app.crud.crud_support import support

router = APIRouter()

@router.get("/faqs", response_model=List[FAQ])
def read_faqs(
    db: Session = Depends(deps.get_db),
    q: Optional[str] = Query(None, description="Término de búsqueda"),
    role: Optional[str] = Query(None, description="Rol del usuario (KOF, CONTRACTOR)")
) -> Any:
    """
    Obtener lista de FAQs filtradas por búsqueda y rol.
    """
    faqs = support.get_faqs(db=db, role=role, search_term=q)
    return faqs

@router.get("/chat-flow", response_model=ChatFlowResponse)
def get_chat_flow(
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Obtener la estructura completa del flujo del chatbot.
    Retorna un JSON optimizado para que el frontend construya el árbol de decisión.
    """
    flow_structure = support.get_chat_flow(db=db)
    return {"nodes": flow_structure}
