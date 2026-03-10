from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CouponType(str, Enum):
    birthday   = "birthday"
    gift_card  = "gift_card"
    referral   = "referral"
    partner    = "partner"
    night_sale = "night_sale"
    campaign   = "campaign"


class DiscountType(str, Enum):
    percent       = "percent"
    fixed_cart    = "fixed_cart"
    fixed_product = "fixed_product"


class CreateCouponRequest(BaseModel):
    model_config = {"str_strip_whitespace": True}

    type: CouponType
    discount_type: DiscountType
    amount: float
    email: Optional[str] = None
    categories: List[int] = []
    products: List[int] = []
    usage_limit: Optional[int] = None
    expiration_days: Optional[int] = None
    expires_at: Optional[datetime] = None
    prefix: Optional[str] = None
    # partner_code: campo libre del body, obligatorio si type=partner (confirmado con Matías)
    partner_code: Optional[str] = None

    @field_validator("partner_code", mode="before")
    @classmethod
    def validate_partner_code(cls, v, info):
        # La validación real se hace en service, pero podemos limpiar el valor aquí
        return v


class UpdateCouponRequest(BaseModel):
    model_config = {"str_strip_whitespace": True}

    # Los campos code, type y discount_type son inmutables — rechazar si vienen
    amount: Optional[float] = None
    email: Optional[str] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: Optional[str] = None


class ValidateCouponRequest(BaseModel):
    email: Optional[str] = None
    product_ids: List[int] = []
    cart_total: Optional[float] = None


class ApplyCouponRequest(BaseModel):
    email: str
    order_id: Optional[str] = None
    product_ids: List[int] = []


class BulkCouponRequest(BaseModel):
    type: CouponType
    discount_type: DiscountType
    amount: float
    categories: List[int] = []
    usage_limit: Optional[int] = None
    expiration_days: Optional[int] = None
    expires_at: Optional[datetime] = None
    quantity: int
    prefix: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def quantity_range(cls, v):
        if v < 1 or v > 500:
            raise ValueError("quantity debe estar entre 1 y 500")
        return v


class CouponResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    wc_id: Optional[int] = None
    code: str
    type: str
    discount_type: str
    amount: float
    allowed_email: Optional[str] = None
    use_count: int
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    status: str
    categories: Optional[list] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
