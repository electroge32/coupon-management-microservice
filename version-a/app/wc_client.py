import httpx
from typing import Optional
from .config import settings
from .logger import coupon_logger


class WooCommerceClient:
    def __init__(self):
        self.base_url = settings.wc_base_url.rstrip("/") + "/wp-json/wc/v3"
        self.auth = (settings.wc_consumer_key, settings.wc_consumer_secret)

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint}"
        response = httpx.get(url, auth=self.auth, params=params, timeout=30, follow_redirects=True)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = httpx.post(url, auth=self.auth, json=data, timeout=30, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            coupon_logger.wc_error(
                endpoint=f"POST {endpoint}",
                error=str(e),
                status_code=e.response.status_code if hasattr(e, 'response') else None
            )
            raise

    def _put(self, endpoint: str, data: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = httpx.put(url, auth=self.auth, json=data, timeout=30, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            coupon_logger.wc_error(
                endpoint=f"PUT {endpoint}",
                error=str(e),
                status_code=e.response.status_code if hasattr(e, 'response') else None
            )
            raise

    def create_coupon(self, data: dict) -> dict:
        return self._post("coupons", data)

    def update_coupon(self, wc_id: int, data: dict) -> dict:
        return self._put(f"coupons/{wc_id}", data)

    def trash_coupon(self, wc_id: int) -> dict:
        url = f"{self.base_url}/coupons/{wc_id}"
        try:
            response = httpx.delete(url, auth=self.auth, params={"force": False}, timeout=30, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            coupon_logger.wc_error(
                endpoint=f"DELETE coupons/{wc_id}",
                error=str(e),
                status_code=e.response.status_code if hasattr(e, 'response') else None
            )
            raise

    def find_coupon_by_code(self, code: str) -> Optional[dict]:
        results = self._get("coupons", {"code": code})
        return results[0] if results else None

    def get_products_by_category(self, category_id: int) -> list:
        # Obtiene product_ids para implementar Category OR Logic (Regla 2)
        products = self._get("products", {"category": category_id, "per_page": 100})
        return [p["id"] for p in products]
