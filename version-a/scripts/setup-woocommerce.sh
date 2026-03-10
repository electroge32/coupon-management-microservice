#!/bin/sh
# =============================================================================
# setup-woocommerce.sh
# Instala y configura WooCommerce automáticamente via WP-CLI
# Ejecutado por el servicio 'wpcli' (imagen wordpress:cli) como one-shot.
#
# IDEMPOTENTE: puede ejecutarse múltiples veces sin crear duplicados.
# =============================================================================

set -e

WP_PATH=/var/www/html
CREDENTIALS_FILE="$WP_PATH/wp-content/wc-credentials.env"

# -----------------------------------------------------------------------------
# Función de logging con timestamp
# -----------------------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# -----------------------------------------------------------------------------
# 1. Esperar MySQL (hasta 60 intentos, 3s entre intentos)
# -----------------------------------------------------------------------------
log "=== Esperando MySQL ==="
attempt=0
until mysqladmin ping -h db -u wpuser -pwppassword --silent --ssl=false 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        log "ERROR: MySQL no respondió después de 60 intentos. Abortando."
        exit 1
    fi
    log "MySQL no disponible todavía (intento $attempt/60). Reintentando en 3s..."
    sleep 3
done
log "MySQL disponible."

# -----------------------------------------------------------------------------
# 2. Esperar WordPress instalado
# -----------------------------------------------------------------------------
log "=== Esperando WordPress ==="
attempt=0
until [ -f "$WP_PATH/wp-includes/version.php" ]; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        log "ERROR: WordPress no estuvo listo después de 60 intentos. Abortando."
        exit 1
    fi
    log "Archivos WordPress no presentes todavía (intento $attempt/60). Reintentando en 5s..."
    sleep 5
done
log "WordPress disponible."

# -----------------------------------------------------------------------------
# 3. Instalar WordPress core si no está instalado (safety net)
# -----------------------------------------------------------------------------
if ! wp core is-installed --allow-root --path="$WP_PATH" 2>/dev/null; then
    log "Instalando WordPress core..."
    wp core install \
        --url=http://wordpress \
        --title="ADIPA Test" \
        --admin_user=admin \
        --admin_password=admin123 \
        --admin_email=admin@adipa.cl \
        --allow-root \
        --path="$WP_PATH" \
        --skip-email
    log "WordPress core instalado."
else
    log "WordPress core ya estaba instalado. Omitiendo."
fi

# -----------------------------------------------------------------------------
# 4. Check idempotencia: si WooCommerce ya activo y credenciales ya existen → exit
# -----------------------------------------------------------------------------
WC_ACTIVE=$(wp plugin is-active woocommerce --allow-root --path="$WP_PATH" 2>/dev/null && echo "yes" || echo "no")
if [ "$WC_ACTIVE" = "yes" ] && [ -f "$CREDENTIALS_FILE" ]; then
    log "WooCommerce ya está activo y las credenciales ya existen en $CREDENTIALS_FILE."
    log "=== Setup WooCommerce completado correctamente (idempotente — sin cambios) ==="
    exit 0
fi

# -----------------------------------------------------------------------------
# 5. Instalar y activar WooCommerce
# -----------------------------------------------------------------------------
if [ "$WC_ACTIVE" != "yes" ]; then
    log "Instalando plugin WooCommerce..."
    wp plugin install woocommerce --activate --allow-root --path="$WP_PATH"
    log "WooCommerce instalado y activado."
else
    log "WooCommerce ya estaba activo. Omitiendo instalación."
fi

# -----------------------------------------------------------------------------
# 6. Configurar WooCommerce básico (país, moneda, dirección)
# -----------------------------------------------------------------------------
log "Configurando WooCommerce..."
wp option update woocommerce_store_address "Calle Falsa 123" --allow-root --path="$WP_PATH"
wp option update woocommerce_store_city "Bogotá" --allow-root --path="$WP_PATH"
wp option update woocommerce_default_country "CO" --allow-root --path="$WP_PATH"
wp option update woocommerce_currency "COP" --allow-root --path="$WP_PATH"
wp option update woocommerce_currency_pos "left" --allow-root --path="$WP_PATH"
wp option update woocommerce_price_decimal_sep "," --allow-root --path="$WP_PATH"
wp option update woocommerce_price_thousand_sep "." --allow-root --path="$WP_PATH"
log "WooCommerce configurado (país: CO, moneda: COP)."

# -----------------------------------------------------------------------------
# 7. Generar API keys de WooCommerce via WP-CLI eval
# Usamos wp eval para insertar directamente en la tabla de la base de datos.
# Esto es más compatible que wp wc key create, que requiere autenticación HTTP.
# -----------------------------------------------------------------------------
log "Generando API keys de WooCommerce..."

WC_KEYS=$(wp eval '
$user_id = 1;
$consumer_key    = "ck_" . wc_rand_hash();
$consumer_secret = "cs_" . wc_rand_hash();
$data = array(
    "user_id"        => $user_id,
    "description"    => "Microservice Key",
    "permissions"    => "read_write",
    "consumer_key"   => wc_api_hash($consumer_key),
    "consumer_secret"=> $consumer_secret,
    "truncated_key"  => substr($consumer_key, -7),
);
global $wpdb;
$wpdb->insert($wpdb->prefix . "woocommerce_api_keys", $data);
echo $consumer_key . ":" . $consumer_secret;
' --allow-root --path="$WP_PATH")

CONSUMER_KEY=$(echo "$WC_KEYS" | cut -d':' -f1)
CONSUMER_SECRET=$(echo "$WC_KEYS" | cut -d':' -f2)

log "API keys generadas (consumer_key: ${CONSUMER_KEY})."

# -----------------------------------------------------------------------------
# 8. Guardar credenciales en archivo compartido con el servicio 'app'
#    Ruta: /var/www/html/wp-content/wc-credentials.env
#    El servicio 'app' monta wp_data en modo lectura y puede leer este archivo.
# -----------------------------------------------------------------------------
log "Guardando credenciales en $CREDENTIALS_FILE..."
cat > "$CREDENTIALS_FILE" <<EOF
WC_BASE_URL=http://wordpress:80
WC_CONSUMER_KEY=${CONSUMER_KEY}
WC_CONSUMER_SECRET=${CONSUMER_SECRET}
EOF
log "Credenciales guardadas."

# -----------------------------------------------------------------------------
# 9. Crear categorías de producto (idempotente: verifica antes de crear)
# -----------------------------------------------------------------------------
log "Creando categorías de producto..."

CAT_CURSOS_ID=$(wp wc product_cat list --user=1 --field=id --name="Cursos" \
    --allow-root --path="$WP_PATH" --format=csv 2>/dev/null | tail -n1)

if [ -z "$CAT_CURSOS_ID" ] || [ "$CAT_CURSOS_ID" = "id" ]; then
    CAT_CURSOS_ID=$(wp wc product_cat create \
        --user=1 \
        --name="Cursos" \
        --slug="cursos" \
        --allow-root \
        --path="$WP_PATH" \
        --porcelain 2>/dev/null)
    log "Categoría 'Cursos' creada con ID: $CAT_CURSOS_ID"
else
    log "Categoría 'Cursos' ya existe con ID: $CAT_CURSOS_ID"
fi

CAT_DIPLOMADOS_ID=$(wp wc product_cat list --user=1 --field=id --name="Diplomados" \
    --allow-root --path="$WP_PATH" --format=csv 2>/dev/null | tail -n1)

if [ -z "$CAT_DIPLOMADOS_ID" ] || [ "$CAT_DIPLOMADOS_ID" = "id" ]; then
    CAT_DIPLOMADOS_ID=$(wp wc product_cat create \
        --user=1 \
        --name="Diplomados" \
        --slug="diplomados" \
        --allow-root \
        --path="$WP_PATH" \
        --porcelain 2>/dev/null)
    log "Categoría 'Diplomados' creada con ID: $CAT_DIPLOMADOS_ID"
else
    log "Categoría 'Diplomados' ya existe con ID: $CAT_DIPLOMADOS_ID"
fi

# -----------------------------------------------------------------------------
# 10. Crear productos seed (idempotente: verifica por nombre antes de crear)
# -----------------------------------------------------------------------------
log "Creando productos seed..."

create_product_if_not_exists() {
    PRODUCT_NAME="$1"
    PRICE="$2"
    CAT_ID="$3"

    EXISTING=$(wp wc product list --user=1 --search="$PRODUCT_NAME" \
        --allow-root --path="$WP_PATH" --format=csv --fields=id,name 2>/dev/null \
        | grep -c "$PRODUCT_NAME" || true)

    if [ "$EXISTING" -eq 0 ]; then
        wp wc product create \
            --user=1 \
            --name="$PRODUCT_NAME" \
            --regular_price="$PRICE" \
            --categories="[{\"id\":$CAT_ID}]" \
            --status=publish \
            --allow-root \
            --path="$WP_PATH" \
            --porcelain 2>/dev/null
        log "Producto creado: '$PRODUCT_NAME' (precio: $PRICE COP, categoría ID: $CAT_ID)"
    else
        log "Producto '$PRODUCT_NAME' ya existe. Omitiendo."
    fi
}

# 2 productos en categoría Cursos
create_product_if_not_exists "Curso de Psicología Básica"    "150000" "$CAT_CURSOS_ID"
create_product_if_not_exists "Curso de Neurociencias"        "200000" "$CAT_CURSOS_ID"

# 2 productos en categoría Diplomados
create_product_if_not_exists "Diplomado en Salud Mental"     "500000" "$CAT_DIPLOMADOS_ID"
create_product_if_not_exists "Diplomado en Terapia Cognitiva" "450000" "$CAT_DIPLOMADOS_ID"

# -----------------------------------------------------------------------------
# 11. Crear mu-plugin para permitir Basic Auth sobre HTTP (local/dev)
#     WooCommerce solo permite Basic Auth sobre HTTPS por defecto.
#     En producción, el proxy (nginx/traefik) forzaría HTTPS.
# -----------------------------------------------------------------------------
MU_PLUGIN_DIR="$WP_PATH/wp-content/mu-plugins"
MU_PLUGIN_FILE="$MU_PLUGIN_DIR/allow-http-basic-auth.php"

if [ ! -f "$MU_PLUGIN_FILE" ]; then
    mkdir -p "$MU_PLUGIN_DIR"
    cat > "$MU_PLUGIN_FILE" << 'MUPLUGIN'
<?php
/**
 * Allow WooCommerce REST API basic auth over HTTP (local/dev environment).
 * In production, HTTPS should be enforced at the reverse proxy level.
 */
add_action("init", function() {
    if (strpos($_SERVER["REQUEST_URI"] ?? "", "/wp-json/wc/") !== false) {
        $_SERVER["HTTPS"] = "on";
    }
}, 1);
MUPLUGIN
    log "mu-plugin allow-http-basic-auth.php creado."
else
    log "mu-plugin allow-http-basic-auth.php ya existe. Omitiendo."
fi

# -----------------------------------------------------------------------------
log "=== Setup WooCommerce completado correctamente ==="
