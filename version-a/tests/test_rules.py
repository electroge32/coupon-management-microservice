"""
Tests de reglas de negocio — CouponService + CodeGenerator
Todos los tests son síncronos. WooCommerce es mock (no hay llamadas HTTP reales).
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models import Coupon
from tests.conftest import birthday_data, referral_data


# ---------------------------------------------------------------------------
# T1: El monto de birthday siempre es 15% sin importar el input
# ---------------------------------------------------------------------------
def test_birthday_amount_forced_to_15(service):
    coupon = service.create(birthday_data(amount=99.0))
    assert float(coupon.amount) == 15.0, "El monto birthday debe ser siempre 15.0"


# ---------------------------------------------------------------------------
# T2: El monto de referral siempre es 3000 sin importar el input
# ---------------------------------------------------------------------------
def test_referral_amount_forced_to_3000(service):
    coupon = service.create(referral_data(amount=9999.0))
    assert float(coupon.amount) == 3000.0, "El monto referral debe ser siempre 3000.0"


# ---------------------------------------------------------------------------
# T3: La validación falla cuando el email no corresponde al cupón
# ---------------------------------------------------------------------------
def test_validate_fails_with_wrong_email(service):
    coupon = service.create(birthday_data(email="owner@example.com"))
    result = service.validate(coupon, "otro@example.com", [])
    assert result["valid"] is False, "Debe fallar con email incorrecto"
    reasons_lower = " ".join(result["reasons"]).lower()
    assert "email" in reasons_lower, "El mensaje de razón debe mencionar 'email'"


# ---------------------------------------------------------------------------
# T4: La validación falla cuando se alcanza el límite de uso
# ---------------------------------------------------------------------------
def test_validate_fails_when_usage_limit_reached(service, db):
    coupon = service.create(birthday_data(usage_limit=1))
    # Simular que ya fue usado el número máximo de veces
    coupon.use_count = 1
    db.commit()

    result = service.validate(coupon, "owner@example.com", [])
    assert result["valid"] is False, "Debe fallar cuando use_count == usage_limit"
    assert any("límite" in r.lower() or "limit" in r.lower() for r in result["reasons"])


# ---------------------------------------------------------------------------
# T5: campaign sin expires_at lanza ValueError
# ---------------------------------------------------------------------------
def test_campaign_requires_explicit_expiration(service):
    data = {
        "type": "campaign",
        "discount_type": "percent",
        "amount": 30.0,
        "email": None,
        "categories": [],
        "products": [],
        "usage_limit": None,
        "expiration_days": None,
        "expires_at": None,  # obligatorio para campaign → debe lanzar excepción
        "prefix": "PROMO",
        "partner_code": None,
    }
    with pytest.raises(ValueError, match="expires_at"):
        service.create(data)


# ---------------------------------------------------------------------------
# T6: CodeGenerator reintenta si el código ya existe en WC
# ---------------------------------------------------------------------------
def test_code_generator_retries_on_collision(service, mock_wc, db):
    # Primera llamada a find_coupon_by_code retorna colisión, segunda retorna None (libre)
    mock_wc.find_coupon_by_code.side_effect = [{"id": 1}, None]

    coupon = service.create(birthday_data())
    assert coupon.code.startswith("BD-"), f"El código debe empezar con 'BD-', obtuvo: {coupon.code}"
    assert mock_wc.find_coupon_by_code.call_count >= 2, "Debe haber consultado WC al menos 2 veces"


# ---------------------------------------------------------------------------
# T7: Category OR Logic — se llama a WC una vez por cada categoría
# ---------------------------------------------------------------------------
def test_category_or_logic_calls_wc_for_each_category(service, mock_wc):
    data = birthday_data(categories=[31, 67])
    service.create(data)

    assert mock_wc.get_products_by_category.call_count == 2, (
        "Debe llamarse a get_products_by_category una vez por categoría"
    )
    called_with = {call.args[0] for call in mock_wc.get_products_by_category.call_args_list}
    assert called_with == {31, 67}, f"Debe consultar las categorías 31 y 67, obtuvo: {called_with}"


# ---------------------------------------------------------------------------
# T8: night_sale siempre expira en 24h sin importar expiration_days
# ---------------------------------------------------------------------------
def test_night_sale_expiration_is_always_24_hours(service):
    data = {
        "type": "night_sale",
        "discount_type": "percent",
        "amount": 40.0,
        "email": None,
        "categories": [],
        "products": [],
        "usage_limit": None,
        "expiration_days": 365,  # debe ignorarse
        "expires_at": None,
        "prefix": None,
        "partner_code": None,
    }
    before = datetime.utcnow()
    coupon = service.create(data)
    after = datetime.utcnow()

    diff = coupon.expires_at - before
    assert timedelta(hours=23) < diff <= timedelta(hours=25), (
        f"night_sale debe expirar en ~24h, obtuvo diff={diff}"
    )


# ---------------------------------------------------------------------------
# T9: Un cupón eliminado (soft delete) falla la validación
# ---------------------------------------------------------------------------
def test_deleted_coupon_fails_validation(service, db):
    coupon = service.create(birthday_data())

    coupon.deleted_at = datetime.utcnow()
    coupon.status = "deleted"
    db.commit()

    result = service.validate(coupon, "owner@example.com", [])
    assert result["valid"] is False, "Un cupón eliminado debe fallar la validación"
    reasons_lower = " ".join(result["reasons"]).lower()
    assert "eliminado" in reasons_lower or "deleted" in reasons_lower


# ---------------------------------------------------------------------------
# T10: bulk continúa creando cupones aunque algunos fallen
# ---------------------------------------------------------------------------
def test_bulk_continues_after_partial_failure(service, mock_wc):
    llamadas = [0]

    def create_coupon_con_fallo(data):
        llamadas[0] += 1
        if llamadas[0] == 5:
            raise RuntimeError("WC timeout simulado")
        return {"id": llamadas[0]}

    mock_wc.create_coupon.side_effect = create_coupon_con_fallo

    data = {
        "type": "birthday",
        "discount_type": "percent",
        "amount": 15.0,
        "email": "bulk@example.com",
        "categories": [],
        "products": [],
        "usage_limit": None,
        "expiration_days": None,
        "expires_at": None,
        "prefix": None,
        "partner_code": None,
        "quantity": 10,
    }
    result = service.create_bulk(data)

    assert result["created"] > 0, "Deben haberse creado cupones exitosos"
    assert result["failed"] > 0, "Debe haber al menos un fallo"
    assert result["created"] + result["failed"] == 10, (
        f"created + failed debe sumar 10, obtuvo {result['created']} + {result['failed']}"
    )
