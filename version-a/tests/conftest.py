import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

from app.database import Base
from app.models import Coupon
from app.wc_client import WooCommerceClient


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def mock_wc():
    wc = MagicMock(spec=WooCommerceClient)
    wc.find_coupon_by_code.return_value = None
    wc.create_coupon.return_value = {"id": 999}
    wc.get_products_by_category.return_value = [101, 102]
    wc.trash_coupon.return_value = {"id": 999, "status": "trash"}
    return wc


@pytest.fixture
def service(db, mock_wc):
    from app.service import CouponService
    s = CouponService(db)
    s.wc = mock_wc
    s.code_gen.wc = mock_wc
    return s


# Helpers compartidos entre tests
def birthday_data(**kwargs) -> dict:
    base = {
        "type": "birthday",
        "discount_type": "percent",
        "amount": 50.0,
        "email": "owner@example.com",
        "categories": [],
        "products": [],
        "usage_limit": None,
        "expiration_days": None,
        "expires_at": None,
        "prefix": None,
        "partner_code": None,
    }
    base.update(kwargs)
    return base


def referral_data(**kwargs) -> dict:
    base = {
        "type": "referral",
        "discount_type": "fixed_cart",
        "amount": 9999.0,
        "email": "ref@example.com",
        "categories": [],
        "products": [],
        "usage_limit": None,
        "expiration_days": None,
        "expires_at": None,
        "prefix": None,
        "partner_code": None,
    }
    base.update(kwargs)
    return base
