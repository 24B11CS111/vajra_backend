import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.types import GUID, JSONBType

class DeviceAction(Base):
    __tablename__ = "device_actions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    source_device_id = Column(String(100), nullable=True)
    target_device_id = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    parameters = Column(JSONBType, default=dict, nullable=False)

    # Status: PENDING, SENT, EXECUTING, SUCCESS, FAILED, OFFLINE, UNAUTHORIZED, UNSUPPORTED
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    result_message = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="device_actions")
