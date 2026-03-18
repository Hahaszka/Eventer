from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    api_keys = relationship("ApiKey", back_populates="owner")

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="api_keys")

class WarehouseProduct(Base):
    __tablename__ = "warehouse_inventory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_code = Column(String(100), nullable=False, unique=True)
    product_name = Column(Text, nullable=False)
    category = Column(String(100))
    embedding = Column(Vector(384))

class VerifiedMapping(Base):
    __tablename__ = "verified_mappings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ocr_text = Column(String, unique=True, index=True, nullable=False)
    sku_code = Column(String(100))
    product_name = Column(Text)