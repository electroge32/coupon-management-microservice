"""
Smoke Test End-to-End
Verifica el flujo completo del servicio sin mocks.

Requiere:
  - Servicio levantado en http://localhost:8000
  - API_KEY configurado en .env
  
Uso:
  python tests/smoke_test.py
"""
import os
import sys
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "test-key")


class SmokeTestError(Exception):
    pass


def health_check():
    """T1: Health check responde correctamente."""
    resp = httpx.get(f"{BASE_URL}/api/v1/health")
    assert resp.status_code == 200, f"Health check falló: {resp.text}"
    data = resp.json()
    assert data["data"]["status"] in ["ok", "degraded"]
    print("✅ T1: Health check OK")


def auth_rejection():
    """T2: Sin API key retorna 401."""
    resp = httpx.get(f"{BASE_URL}/api/v1/coupons")
    assert resp.status_code == 401, "Debe rechazar requests sin API key"
    print("✅ T2: Auth rejection OK")


def create_birthday_coupon():
    """T3: Crear cupón birthday fuerza monto a 15%."""
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons",
        headers={"X-API-Key": API_KEY},
        json={
            "type": "birthday",
            "discount_type": "percent",
            "amount": 99.0,
            "email": "test@example.com",
        },
    )
    assert resp.status_code == 201, f"Creación falló: {resp.text}"
    data = resp.json()
    assert data["data"]["amount"] == 15.0, "Birthday debe forzar amount a 15.0"
    assert data["data"]["code"].startswith("BD-")
    print("✅ T3: Birthday coupon creation OK")
    return data["data"]["code"]


def create_referral_coupon():
    """T4: Crear cupón referral fuerza monto a 3000."""
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons",
        headers={"X-API-Key": API_KEY},
        json={
            "type": "referral",
            "discount_type": "fixed_cart",
            "amount": 9999.0,
            "email": "ref@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["data"]["amount"] == 3000.0, "Referral debe forzar amount a 3000.0"
    print("✅ T4: Referral coupon creation OK")
    return data["data"]["code"]


def validate_wrong_email(code: str):
    """T5: Validación con email incorrecto falla."""
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons/{code}/validate",
        headers={"X-API-Key": API_KEY},
        json={"email": "wrong@example.com", "product_ids": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["valid"] is False
    assert any("email" in r.lower() for r in data["data"]["reasons"])
    print("✅ T5: Validate wrong email OK")


def validate_and_apply(code: str):
    """T6: Validación correcta y aplicación de cupón."""
    # Validar
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons/{code}/validate",
        headers={"X-API-Key": API_KEY},
        json={"email": "test@example.com", "product_ids": []},
    )
    assert resp.json()["data"]["valid"] is True
    
    # Aplicar
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons/{code}/apply",
        headers={"X-API-Key": API_KEY},
        json={"email": "test@example.com", "order_id": "TEST-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["use_count"] == 1
    print("✅ T6: Validate and apply OK")


def campaign_requires_expiration():
    """T7: Campaign sin expires_at retorna 400."""
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons",
        headers={"X-API-Key": API_KEY},
        json={
            "type": "campaign",
            "discount_type": "percent",
            "amount": 20.0,
            "prefix": "PROMO",
        },
    )
    assert resp.status_code == 400, "Campaign sin expires_at debe fallar"
    print("✅ T7: Campaign validation OK")


def create_campaign_coupon():
    """T8: Crear campaign con expires_at funciona."""
    future = (datetime.utcnow() + timedelta(days=7)).isoformat()
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons",
        headers={"X-API-Key": API_KEY},
        json={
            "type": "campaign",
            "discount_type": "percent",
            "amount": 20.0,
            "prefix": "PROMO",
            "expires_at": future,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["data"]["code"].startswith("PROMO-")
    print("✅ T8: Campaign creation OK")
    return data["data"]["code"]


def list_coupons():
    """T9: Listado de cupones con filtros."""
    resp = httpx.get(
        f"{BASE_URL}/api/v1/coupons",
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert "total" in data["meta"]
    print("✅ T9: List coupons OK")


def bulk_creation():
    """T10: Creación bulk parcial."""
    resp = httpx.post(
        f"{BASE_URL}/api/v1/coupons/bulk",
        headers={"X-API-Key": API_KEY},
        json={
            "quantity": 3,
            "type": "birthday",
            "discount_type": "percent",
            "amount": 50.0,
            "email": "bulk@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["data"]["created"] == 3
    assert data["data"]["failed"] == 0
    print("✅ T10: Bulk creation OK")


def run_all():
    print(f"\n🔥 Smoke Tests E2E — {BASE_URL}\n")
    
    try:
        health_check()
        auth_rejection()
        
        birthday_code = create_birthday_coupon()
        referral_code = create_referral_coupon()
        
        validate_wrong_email(birthday_code)
        validate_and_apply(birthday_code)
        
        campaign_requires_expiration()
        campaign_code = create_campaign_coupon()
        
        list_coupons()
        bulk_creation()
        
        print("\n✅ TODOS LOS SMOKE TESTS PASARON\n")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ ASSERT FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all())
