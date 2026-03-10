import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from .logger import coupon_logger

CHARSET = string.ascii_uppercase + string.digits


class CodeGenerator:
    def __init__(self, db: Session, wc: "WooCommerceClient"):
        self.db = db
        self.wc = wc

    def _random(self, length: int) -> str:
        return "".join(random.choices(CHARSET, k=length))

    def generate(self, coupon_type: str, options: dict = None) -> str:
        opts = options or {}
        today = datetime.now().strftime("%Y%m%d")

        patterns = {
            "birthday":   f"BD-{self._random(6)}",
            "gift_card":  f"GC-{self._random(8)}",
            "referral":   f"REF-{self._random(6)}",
            # partner_code viene del body del request — valor libre, obligatorio para tipo partner
            "partner":    f"{opts['partner_code']}-{self._random(4)}",
            "night_sale": f"NS-{today}-{self._random(4)}",
            "campaign":   f"{opts.get('prefix', 'CAMP')}-{self._random(6)}",
        }

        return patterns[coupon_type]

    def generate_unique(self, coupon_type: str, options: dict = None) -> str:
        for attempt in range(1, 4):
            code = self.generate(coupon_type, options)
            exists_local = self._exists_locally(code)
            exists_wc = self._exists_in_wc(code)
            
            if not exists_local and not exists_wc:
                return code
            
            # Loggear colisión para trazabilidad
            coupon_logger.code_collision(
                code_attempt=code,
                coupon_type=coupon_type,
                attempt_number=attempt
            )

        raise RuntimeError(
            f"No se pudo generar código único para tipo '{coupon_type}' en 3 intentos"
        )

    def _exists_locally(self, code: str) -> bool:
        from .models import Coupon
        return self.db.query(Coupon).filter(Coupon.code == code).first() is not None

    def _exists_in_wc(self, code: str) -> bool:
        return self.wc.find_coupon_by_code(code) is not None
