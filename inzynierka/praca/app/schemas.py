from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class PasswordUpdate(BaseModel):
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class InvoiceItemReq(BaseModel):
    item_text: str

class MatchResult(BaseModel):
    faktura: str
    baza: Optional[str]
    is_match: bool
    confidence_score: float
    reasoning: str

class ProductBase(BaseModel):
    sku: str
    name: str
    cat: Optional[str] = "Manual"

class MappingBase(BaseModel):
    ocr_text: str
    sku_code: str
    product_name: str