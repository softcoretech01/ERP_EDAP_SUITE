from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..db.database import Base
from .role import role_permissions

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255))

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
