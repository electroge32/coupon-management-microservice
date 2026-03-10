"""
Structured JSON Logger para el servicio de cupones.
Formato consistente con trazabilidad de eventos de negocio.
"""
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional


class JsonFormatter(logging.Formatter):
    """Formatter que emite logs en formato JSON por línea."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "action": getattr(record, "action", "unknown"),
        }
        
        # Copiar campos extra del LogRecord (excluir stdlib)
        excluded = {
            "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno",
            "funcName", "created", "msecs", "relativeCreated", "thread",
            "threadName", "processName", "process", "message", "name",
            "taskName", "asctime"
        }
        
        for key, value in record.__dict__.items():
            if key not in excluded and not key.startswith("_"):
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


def get_logger(name: str = "coupons") -> logging.Logger:
    """Obtiene logger configurado con formato JSON."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


class CouponLogger:
    """Wrapper para logging semántico de eventos de cupones."""
    
    def __init__(self):
        self.logger = get_logger("coupons")
    
    def _log(self, level: int, action: str, **kwargs):
        """Emite log con nivel y action específicos."""
        extra = {"action": action, **kwargs}
        self.logger.log(level, "", extra=extra)
    
    def coupon_created(
        self,
        code: str,
        coupon_type: str,
        amount: float,
        wc_id: Optional[int],
        duration_ms: int
    ):
        """Log cuando se crea un cupón exitosamente."""
        self._log(
            logging.INFO,
            "coupon.created",
            coupon_code=code,
            type=coupon_type,
            amount=amount,
            wc_id=wc_id,
            duration_ms=duration_ms
        )
    
    def coupon_applied(
        self,
        code: str,
        email: str,
        order_id: Optional[str],
        use_count: int
    ):
        """Log cuando se aplica un cupón."""
        self._log(
            logging.INFO,
            "coupon.applied",
            coupon_code=code,
            email=email,
            order_id=order_id,
            use_count=use_count
        )
    
    def validation_failed(self, code: str, reasons: list):
        """Log cuando la validación de un cupón falla."""
        self._log(
            logging.INFO,
            "coupon.validation_failed",
            coupon_code=code,
            reasons=reasons
        )
    
    def wc_error(self, endpoint: str, error: str, status_code: Optional[int] = None):
        """Log cuando hay error en llamada a WooCommerce."""
        self._log(
            logging.ERROR,
            "woocommerce.error",
            wc_endpoint=endpoint,
            error_message=error,
            status_code=status_code
        )
    
    def code_collision(
        self,
        code_attempt: str,
        coupon_type: str,
        attempt_number: int
    ):
        """Log cuando hay colisión de código y se reintenta."""
        self._log(
            logging.WARNING,
            "code.collision",
            code_attempt=code_attempt,
            type=coupon_type,
            attempt_number=attempt_number
        )
    
    def bulk_operation(
        self,
        quantity: int,
        coupons_created: int,
        coupons_failed: int
    ):
        """Log resumen de operación bulk."""
        self._log(
            logging.INFO,
            "coupon.bulk_created",
            quantity=quantity,
            coupons_created=coupons_created,
            coupons_failed=coupons_failed
        )


# Singleton para uso global
coupon_logger = CouponLogger()
