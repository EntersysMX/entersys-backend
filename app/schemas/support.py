from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

# --- FAQ Schemas ---

class FAQBase(BaseModel):
    question: str
    answer: str
    category: str = 'GENERAL'
    target_role: str = 'ALL'
    priority: int = 0
    is_active: bool = True

class FAQCreate(FAQBase):
    pass

class FAQUpdate(FAQBase):
    pass

class FAQ(FAQBase):
    id: UUID

    class Config:
        from_attributes = True

# --- Chatbot Schemas ---

class ChatOptionBase(BaseModel):
    label: str
    next_node_key: Optional[str] = None

class ChatOptionCreate(ChatOptionBase):
    parent_node_key: str

class ChatOption(ChatOptionBase):
    id: int
    parent_node_key: str

    class Config:
        from_attributes = True

class ChatNodeBase(BaseModel):
    message_text: str
    node_type: str = 'MENU'  # 'MENU', 'FINAL_LINK', 'FINAL_TEXT'
    external_link: Optional[str] = None

class ChatNodeCreate(ChatNodeBase):
    node_key: str

class ChatNode(ChatNodeBase):
    node_key: str
    options: List[ChatOption] = []

    class Config:
        from_attributes = True

# --- API Responses ---

class ChatFlowResponse(BaseModel):
    """
    Estructura optimizada para el frontend:
    {
        "start": {
            "message": "Hola...",
            "type": "MENU",
            "options": [
                {"label": "Opción A", "next": "node_a"},
                ...
            ]
        },
        ...
    }
    """
    nodes: Dict[str, Any]
