"""
Simplified User Models for ModuleX
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..core.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    external_id = Column(String, unique=True, index=True, nullable=False)  # Client provided ID
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tool_auths = relationship("UserToolAuth", back_populates="user", cascade="all, delete-orphan")


class UserToolAuth(Base):
    """User tool authentication - simplified"""
    __tablename__ = "user_tool_auths"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)  # github, slack, etc.
    
    # Authentication data (encrypted)
    encrypted_credentials = Column(Text, nullable=False)
    is_authenticated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)  # New field: whether the tool is active/enabled
    disabled_actions = Column(JSON, default=list)  # List of disabled action names for this tool
    auth_expires_at = Column(DateTime, nullable=True)
    
    # Metadata
    last_auth_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="tool_auths") 