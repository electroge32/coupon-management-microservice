from sqlalchemy import Column, Integer, String, Numeric, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id            = Column(Integer, primary_key=True, index=True)
    wc_id         = Column(Integer, nullable=True)
    code          = Column(String(50), unique=True, nullable=False, index=True)
    type          = Column(String(20), nullable=False)
    discount_type = Column(String(20), nullable=False)
    amount        = Column(Numeric(10, 2), nullable=False)
    allowed_email = Column(String(255), nullable=True)
    use_count     = Column(Integer, default=0)
    usage_limit   = Column(Integer, nullable=True)
    expires_at    = Column(DateTime, nullable=True)
    status        = Column(String(10), default="active")
    categories    = Column(JSON, nullable=True)
    meta          = Column("metadata", JSON, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at    = Column(DateTime, nullable=True)

    usages = relationship("CouponUsage", back_populates="coupon")

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()

    def has_reached_limit(self) -> bool:
        if self.usage_limit is None:
            return False
        return self.use_count >= self.usage_limit


class CouponUsage(Base):
    __tablename__ = "coupon_usages"

    id        = Column(Integer, primary_key=True, index=True)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    email     = Column(String(255), nullable=True)
    order_id  = Column(String(100), nullable=True)
    used_at   = Column(DateTime, default=datetime.utcnow)

    coupon = relationship("Coupon", back_populates="usages")
