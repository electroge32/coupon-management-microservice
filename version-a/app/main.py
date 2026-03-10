from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Coupon
from .schemas import (
    CreateCouponRequest,
    UpdateCouponRequest,
    BulkCouponRequest,
    ValidateCouponRequest,
    ApplyCouponRequest,
)
from .service import CouponService
from .config import settings

app = FastAPI(title="ADIPA Coupon Service", version="1.0.0")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Autenticación por header
# ---------------------------------------------------------------------------
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Helpers de respuesta — envelope consistente
# ---------------------------------------------------------------------------
def ok(data, status_code: int = 200, meta: dict = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "data":  data,
            "meta":  {"timestamp": datetime.utcnow().isoformat(), **(meta or {})},
            "error": None,
        },
    )


def fail(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "data":  None,
            "meta":  {"timestamp": datetime.utcnow().isoformat()},
            "error": message,
        },
    )


def _coupon_to_dict(coupon: Coupon) -> dict:
    return {
        "id":            coupon.id,
        "wc_id":         coupon.wc_id,
        "code":          coupon.code,
        "type":          coupon.type,
        "discount_type": coupon.discount_type,
        "amount":        float(coupon.amount),
        "allowed_email": coupon.allowed_email,
        "use_count":     coupon.use_count,
        "usage_limit":   coupon.usage_limit,
        "expires_at":    coupon.expires_at.isoformat() if coupon.expires_at else None,
        "status":        coupon.status,
        "categories":    coupon.categories,
        "created_at":    coupon.created_at.isoformat() if coupon.created_at else None,
        "updated_at":    coupon.updated_at.isoformat() if coupon.updated_at else None,
        "deleted_at":    coupon.deleted_at.isoformat() if coupon.deleted_at else None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/coupons — crear cupón
# ---------------------------------------------------------------------------
@app.post("/api/v1/coupons", dependencies=[Depends(verify_api_key)])
def create_coupon(body: CreateCouponRequest, db: Session = Depends(get_db)):
    try:
        service = CouponService(db)
        coupon = service.create(body.model_dump())
        return ok(_coupon_to_dict(coupon), 201)
    except ValueError as e:
        return fail(str(e), 400)
    except Exception as e:
        return fail("Error interno al crear el cupón", 500)


# ---------------------------------------------------------------------------
# POST /api/v1/coupons/bulk — crear cupones en lote
# ---------------------------------------------------------------------------
@app.post("/api/v1/coupons/bulk", dependencies=[Depends(verify_api_key)])
def create_bulk(body: BulkCouponRequest, db: Session = Depends(get_db)):
    try:
        service = CouponService(db)
        result = service.create_bulk(body.model_dump())
        return ok(result, 200)
    except ValueError as e:
        return fail(str(e), 400)
    except Exception as e:
        return fail("Error interno al procesar el lote", 500)


# ---------------------------------------------------------------------------
# GET /api/v1/coupons — listar cupones con filtros y paginación
# ---------------------------------------------------------------------------
@app.get("/api/v1/coupons", dependencies=[Depends(verify_api_key)])
def list_coupons(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Coupon).filter(Coupon.deleted_at.is_(None))

    if type:   query = query.filter(Coupon.type == type)
    if status: query = query.filter(Coupon.status == status)
    if email:  query = query.filter(Coupon.allowed_email == email)
    if code:   query = query.filter(Coupon.code.ilike(f"%{code}%"))

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return ok(
        [_coupon_to_dict(c) for c in items],
        meta={"total": total, "per_page": per_page, "current_page": page, "last_page": -(-total // per_page)},
    )


# ---------------------------------------------------------------------------
# GET /api/v1/coupons/{code} — obtener cupón por código
# ---------------------------------------------------------------------------
@app.get("/api/v1/coupons/{code}", dependencies=[Depends(verify_api_key)])
def get_coupon(code: str, db: Session = Depends(get_db)):
    code = code.upper()
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon:
        return fail("Cupón no encontrado", 404)
    return ok(_coupon_to_dict(coupon))


# ---------------------------------------------------------------------------
# PUT /api/v1/coupons/{code} — actualizar cupón
# ---------------------------------------------------------------------------
@app.put("/api/v1/coupons/{code}", dependencies=[Depends(verify_api_key)])
def update_coupon(code: str, body: UpdateCouponRequest, db: Session = Depends(get_db)):
    code = code.upper()
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.deleted_at.is_(None)).first()
    if not coupon:
        return fail("Cupón no encontrado", 404)
    try:
        service = CouponService(db)
        # Pasar solo los campos que vinieron en el body (excluir None)
        data = {k: v for k, v in body.model_dump().items() if v is not None}
        coupon = service.update(coupon, data)
        return ok(_coupon_to_dict(coupon))
    except ValueError as e:
        return fail(str(e), 400)
    except Exception as e:
        return fail("Error interno al actualizar el cupón", 500)


# ---------------------------------------------------------------------------
# DELETE /api/v1/coupons/{code} — soft delete
# ---------------------------------------------------------------------------
@app.delete("/api/v1/coupons/{code}", dependencies=[Depends(verify_api_key)])
def delete_coupon(code: str, db: Session = Depends(get_db)):
    code = code.upper()
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.deleted_at.is_(None)).first()
    if not coupon:
        return fail("Cupón no encontrado", 404)

    coupon.deleted_at = datetime.utcnow()
    coupon.status = "deleted"

    try:
        if coupon.wc_id:
            service = CouponService(db)
            service.wc.trash_coupon(coupon.wc_id)
    except Exception:
        pass  # si WC falla, el soft delete local igual se guarda

    db.commit()
    db.refresh(coupon)

    return ok({"code": coupon.code, "deleted_at": coupon.deleted_at.isoformat()})


# ---------------------------------------------------------------------------
# POST /api/v1/coupons/{code}/validate — validar cupón sin aplicarlo
# ---------------------------------------------------------------------------
@app.post("/api/v1/coupons/{code}/validate", dependencies=[Depends(verify_api_key)])
def validate_coupon(code: str, body: ValidateCouponRequest, db: Session = Depends(get_db)):
    code = code.upper()
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon:
        return fail("Cupón no encontrado", 404)

    service = CouponService(db)
    result = service.validate(coupon, body.email, body.product_ids)
    return ok(result)


# ---------------------------------------------------------------------------
# POST /api/v1/coupons/{code}/apply — aplicar cupón
# ---------------------------------------------------------------------------
@app.post("/api/v1/coupons/{code}/apply", dependencies=[Depends(verify_api_key)])
def apply_coupon(code: str, body: ApplyCouponRequest, db: Session = Depends(get_db)):
    code = code.upper()
    coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.deleted_at.is_(None)).first()
    if not coupon:
        return fail("Cupón no encontrado", 404)
    try:
        service = CouponService(db)
        coupon = service.apply(coupon, body.email, body.order_id, body.product_ids)
        return ok({
            "code":        coupon.code,
            "use_count":   coupon.use_count,
            "usage_limit": coupon.usage_limit,
            "applied_at":  datetime.utcnow().isoformat(),
        })
    except ValueError as e:
        return fail(str(e), 422)
    except Exception as e:
        return fail("Error interno al aplicar el cupón", 500)


# ---------------------------------------------------------------------------
# GET /api/v1/health — estado del servicio (sin autenticación)
# ---------------------------------------------------------------------------
@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False

    wc_ok = True
    try:
        from .wc_client import WooCommerceClient
        WooCommerceClient()._get("coupons", {"per_page": 1})
    except Exception:
        wc_ok = False

    overall_ok = db_ok and wc_ok
    status = "ok" if overall_ok else "degraded"
    http_status = 200 if overall_ok else 503

    return JSONResponse(
        status_code=http_status,
        content={
            "data": {
                "status":  status,
                "version": "1.0.0",
                "checks": {
                    "database":    "ok" if db_ok else "error",
                    "woocommerce": "ok" if wc_ok else "error",
                },
            },
            "meta":  {"timestamp": datetime.utcnow().isoformat()},
            "error": None,
        },
    )
