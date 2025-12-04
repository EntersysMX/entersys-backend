from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base

class SupportFAQ(Base):
    __tablename__ = "sys_support_faq"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default='GENERAL')
    target_role = Column(String(20), nullable=False, default='ALL')  # 'CONTRACTOR', 'KOF', 'ALL'
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)

class ChatNode(Base):
    __tablename__ = "sys_chat_nodes"

    node_key = Column(String(50), primary_key=True, index=True)
    message_text = Column(Text, nullable=False)
    node_type = Column(String(20), nullable=False, default='MENU')  # 'MENU', 'FINAL_LINK', 'FINAL_TEXT'
    external_link = Column(String(255), nullable=True)

    options = relationship("ChatOption", back_populates="parent_node", foreign_keys="ChatOption.parent_node_key")

class ChatOption(Base):
    __tablename__ = "sys_chat_options"

    id = Column(Integer, primary_key=True, index=True)
    parent_node_key = Column(String(50), ForeignKey("sys_chat_nodes.node_key"), nullable=False)
    label = Column(String(100), nullable=False)
    next_node_key = Column(String(50), ForeignKey("sys_chat_nodes.node_key"), nullable=True)

    parent_node = relationship("ChatNode", back_populates="options", foreign_keys=[parent_node_key])
    next_node = relationship("ChatNode", foreign_keys=[next_node_key])
