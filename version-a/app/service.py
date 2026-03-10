import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from .models import Coupon, CouponUsage
from .wc_client import WooCommerceClient
from .code_generator import CodeGenerator
from .config import settings
from .logger import coupon_logger


class CouponService:
    def __init__(self, db: Session):
        self.db = db
        self.wc = WooCommerceClient()
        self.code_gen = CodeGenerator(db, self.wc)

    # --- Regla 5: forzar monto por tipo de cupón ---
    def _enforce_amount(self, coupon_type: str, discount_type: str, amount: float) -> float:
        if coupon_type == "birthday":
            return 15.0
        if coupon_type == "referral":
            return 3000.0
        if coupon_type == "night_sale" and amount > 50:
            return 50.0
        if discount_type == "percent" and amount > 100:
            return 100.0
        if discount_type != "percent" and amount > settings.max_fixed_discount:
            return float(settings.max_fixed_discount)
        return amount

    # --- Regla 6: calcular expiración por tipo ---
    def _calculate_expiration(
        self,
        coupon_type: str,
        expiration_days: Optional[int],
        expires_at: Optional[datetime],
    ) -> datetime:
        now = datetime.utcnow()

        if coupon_type in ("birthday", "referral"):
            return now + timedelta(days=30)
        if coupon_type == "partner":
            return now + timedelta(days=90)
        if coupon_type == "night_sale":
            return now + timedelta(hours=24)
        if coupon_type == "gift_card":
            days = min(expiration_days or 365, 365)
            return now + timedelta(days=days)
        if coupon_type == "campaign":
            if not expires_at:
                raise ValueError(
                    "El tipo 'campaign' requiere una fecha de expiración explícita en 'expires_at'"
                )
            return expires_at

        return now + timedelta(days=expiration_days or 30)

    # --- Regla 2: Category OR Logic ---
    def _resolve_category_products(self, category_ids: list) -> list:
        if not category_ids:
            return []

        # WooCommerce aplica AND entre categorías cuando se pasan como filtro de cupón.
        # Para obtener comportamiento OR, resolvemos cada categoría a product_ids
        # y enviamos el conjunto unificado como product_ids al cupón.
        product_ids = set()
        for cat_id in category_ids:
            ids = self.wc.get_products_by_category(cat_id)
            product_ids.update(ids)

        return list(product_ids)

    # --- Reglas 3 y 4: validación completa de un cupón ---
    def validate(self, coupon: Coupon, email: Optional[str], product_ids: list) -> dict:
        reasons = []

        if coupon.deleted_at is not None or coupon.status == "deleted":
            reasons.append("El cupón ha sido eliminado")

        if coupon.is_expired():
            reasons.append("El cupón ha expirado")

        if coupon.has_reached_limit():
            reasons.append("El cupón ha alcanzado su límite de usos")

        # Regla 4: restricción de email almacenada localmente (WC tiene bugs con email_restrictions)
        if coupon.allowed_email and email and coupon.allowed_email.lower() != email.lower():
            reasons.append("El email no corresponde al cupón")

        if product_ids and coupon.meta:
            restricted = coupon.meta.get("restricted_product_ids", [])
            if restricted and not set(product_ids) & set(restricted):
                reasons.append("Ningún producto del carrito aplica para este cupón")

        return {"valid": len(reasons) == 0, "reasons": reasons}

    # --- Crear cupón individual ---
    def create(self, data: dict) -> Coupon:
        start_time = time.time()
        coupon_type = data["type"]

        if coupon_type == "partner" and not data.get("partner_code"):
            raise ValueError("El campo 'partner_code' es obligatorio para tipo partner")
        if coupon_type == "campaign" and not data.get("prefix"):
            raise ValueError("El campo 'prefix' es obligatorio para tipo campaign")
        if coupon_type in ("birthday", "gift_card", "referral") and not data.get("email"):
            raise ValueError(f"El campo 'email' es obligatorio para tipo {coupon_type}")

        amount = self._enforce_amount(coupon_type, data["discount_type"], data["amount"])
        exp_date = self._calculate_expiration(
            coupon_type,
            data.get("expiration_days"),
            data.get("expires_at"),
        )

        code = self.code_gen.generate_unique(coupon_type, {
            "prefix":       data.get("prefix"),
            "partner_code": data.get("partner_code"),
        })

        # Regla 2: resolver categorías a product_ids para lograr OR logic
        product_ids = self._resolve_category_products(data.get("categories", []))
        product_ids.extend(data.get("products", []))
        product_ids = list(set(product_ids))

        # Nota: NO incluir email_restrictions — WooCommerce tiene bugs conocidos con este campo.
        # La restricción de email se almacena localmente en allowed_email y se valida en /validate.
        wc_payload = {
            "code":           code,
            "discount_type":  data["discount_type"],
            "amount":         str(amount),
            "date_expires":   exp_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "usage_limit":    data.get("usage_limit"),
            "individual_use": coupon_type != "campaign",  # campaign es stackable
            "product_ids":    product_ids if product_ids else [],
        }

        wc_coupon = self.wc.create_coupon(wc_payload)

        coupon = Coupon(
            wc_id         = wc_coupon["id"],
            code          = code,
            type          = coupon_type,
            discount_type = data["discount_type"],
            amount        = amount,
            allowed_email = data.get("email"),
            usage_limit   = data.get("usage_limit"),
            expires_at    = exp_date,
            categories    = data.get("categories", []),
            meta          = {"restricted_product_ids": product_ids},
        )

        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)

        duration_ms = int((time.time() - start_time) * 1000)
        coupon_logger.coupon_created(
            code=code,
            coupon_type=coupon_type,
            amount=amount,
            wc_id=wc_coupon.get("id"),
            duration_ms=duration_ms
        )

        return coupon

    # --- Aplicar cupón ---
    def apply(self, coupon: Coupon, email: str, order_id: Optional[str], product_ids: list = None) -> Coupon:
        validation = self.validate(coupon, email, product_ids or [])
        if not validation["valid"]:
            coupon_logger.validation_failed(coupon.code, validation["reasons"])
            raise ValueError("; ".join(validation["reasons"]))

        usage = CouponUsage(
            coupon_id = coupon.id,
            email     = email,
            order_id  = order_id,
            used_at   = datetime.utcnow(),
        )
        self.db.add(usage)

        coupon.use_count += 1
        self.db.commit()
        self.db.refresh(coupon)

        coupon_logger.coupon_applied(
            code=coupon.code,
            email=email,
            order_id=order_id,
            use_count=coupon.use_count
        )

        return coupon

    # --- Actualizar cupón ---
    def update(self, coupon: Coupon, data: dict) -> Coupon:
        campos_inmutables = {"code", "type", "discount_type"}
        intentados = campos_inmutables & set(data.keys())
        if intentados:
            raise ValueError(f"Los campos {', '.join(intentados)} son inmutables")

        if "amount" in data:
            coupon.amount = self._enforce_amount(coupon.type, coupon.discount_type, data["amount"])
        if "email" in data:
            coupon.allowed_email = data["email"]
        if "usage_limit" in data:
            coupon.usage_limit = data["usage_limit"]
        if "expires_at" in data:
            coupon.expires_at = data["expires_at"]
        if "status" in data:
            coupon.status = data["status"]

        coupon.updated_at = datetime.utcnow()

        # Sincronizar cambios en WooCommerce si tiene wc_id
        if coupon.wc_id:
            wc_update = {}
            if "amount" in data:
                wc_update["amount"] = str(coupon.amount)
            if "expires_at" in data and coupon.expires_at:
                wc_update["date_expires"] = coupon.expires_at.strftime("%Y-%m-%dT%H:%M:%S")
            if "usage_limit" in data:
                wc_update["usage_limit"] = coupon.usage_limit
            if wc_update:
                self.wc.update_coupon(coupon.wc_id, wc_update)

        self.db.commit()
        self.db.refresh(coupon)

        return coupon

    # --- Crear en lotes ---
    def create_bulk(self, data: dict) -> dict:
        quantity = data["quantity"]
        created, failed, errors = 0, 0, []

        batch_size = 20
        for i in range(0, quantity, batch_size):
            for _ in range(i, min(i + batch_size, quantity)):
                try:
                    self.create(data)
                    created += 1
                except Exception as e:
                    failed += 1
                    errors.append(str(e))

        coupon_logger.bulk_operation(quantity, coupons_created=created, coupons_failed=failed)

        return {"created": created, "failed": failed, "errors": errors}
