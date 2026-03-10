#!/bin/sh
# Carga las credenciales de WooCommerce generadas por wpcli (si existen)
# y las exporta como variables de entorno antes de arrancar la app.

CREDS_FILE="/var/www/html/wp-content/wc-credentials.env"

if [ -f "$CREDS_FILE" ]; then
    echo "[entrypoint] Cargando credenciales WooCommerce desde $CREDS_FILE"
    # shellcheck disable=SC1090
    set -a
    . "$CREDS_FILE"
    set +a
else
    echo "[entrypoint] AVISO: $CREDS_FILE no encontrado. Usando variables del entorno."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
