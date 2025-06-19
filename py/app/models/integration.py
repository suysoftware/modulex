"""
Integration Models for Dynamic Tool Management
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..core.database import Base

class AvailableTool(Base):
    """Available tools that can be installed (from integrations/ folder)"""
    __tablename__ = "available_tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    author = Column(String(255))
    version = Column(String(50))
    actions = Column(JSONB, nullable=False, default=list)  # [{"name": "action1", "description": "..."}, ...]
    environment_variables = Column(JSONB, nullable=False, default=list)  # [{"name": "VAR_NAME", "description": "...", "sample_format": "..."}, ...]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class InstalledTool(Base):
    """Tools that are currently installed and active in the system"""
    __tablename__ = "installed_tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    author = Column(String(255))
    version = Column(String(50))
    enabled_actions = Column(JSONB, nullable=False, default=list)  # [{"name": "action1", "description": "..."}, ...]
    disabled_actions = Column(JSONB, nullable=False, default=list)  # [{"name": "action2", "description": "..."}, ...]
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class InstalledToolVariable(Base):
    """Environment variables for installed tools (encrypted storage)"""
    __tablename__ = "installed_tools_variables"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # tool name (not unique)
    variable_key = Column(String(255), nullable=False)
    variable_value = Column(Text, nullable=False)  # encrypted value
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('name', 'variable_key', name='uq_tool_variable'),
    ) 