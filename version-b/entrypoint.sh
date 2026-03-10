#!/bin/sh
# =============================================================================
# entrypoint.sh — Laravel Coupon Service
# Carga las credenciales WooCommerce generadas por el servicio wpcli,
# las escribe en el .env para que php artisan serve las herede correctamente,
# ejecuta las migraciones y arranca php artisan serve.
# =============================================================================

set -e

CREDENTIALS_FILE="/var/www/html/wp-content/wc-credentials.env"
ENV_FILE="/var/www/app/.env"

echo "[entrypoint] Esperando credenciales WooCommerce en $CREDENTIALS_FILE..."
attempt=0
until [ -f "$CREDENTIALS_FILE" ]; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "[entrypoint] ERROR: wc-credentials.env no apareció después de 30 intentos. Abortando."
        exit 1
    fi
    echo "[entrypoint] Archivo no disponible todavía (intento $attempt/30). Reintentando en 5s..."
    sleep 5
done

echo "[entrypoint] Leyendo credenciales WooCommerce..."
# shellcheck source=/dev/null
. "$CREDENTIALS_FILE"

echo "[entrypoint] Actualizando $ENV_FILE con credenciales reales..."
sed -i "s|^WC_BASE_URL=.*|WC_BASE_URL=${WC_BASE_URL}|" "$ENV_FILE"
sed -i "s|^WC_CONSUMER_KEY=.*|WC_CONSUMER_KEY=${WC_CONSUMER_KEY}|" "$ENV_FILE"
sed -i "s|^WC_CONSUMER_SECRET=.*|WC_CONSUMER_SECRET=${WC_CONSUMER_SECRET}|" "$ENV_FILE"

echo "[entrypoint] Credenciales escritas (WC_BASE_URL=$WC_BASE_URL, KEY=${WC_CONSUMER_KEY:0:12}...)."

echo "[entrypoint] Descubriendo paquetes Laravel..."
php artisan package:discover --ansi 2>/dev/null || true

echo "[entrypoint] Ejecutando migraciones..."
php artisan migrate --force

echo "[entrypoint] Iniciando servidor Laravel en 0.0.0.0:8000..."
exec php artisan serve --host=0.0.0.0 --port=8000
