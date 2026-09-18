import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.types import GUID, JSONBType

class Device(Base):
    __tablename__ = "devices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    device_id = Column(String(100), nullable=False, index=True)
    device_type = Column(String(50), nullable=False, default="desktop")  # mobile, desktop, web
    device_name = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False, default="windows")     # windows, android, macos, linux, etc.
    app_version = Column(String(50), nullable=True)
    
    capabilities = Column(JSONBType, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="devices")
