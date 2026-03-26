# Coupon Management Microservice — WooCommerce REST API Wrapper

> Microservicio de gestión de cupones que envuelve la API REST de WooCommerce v3 con lógica de negocio propia. Entregado en dos implementaciones paralelas: **FastAPI (Python)** y **Laravel (PHP)**.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![PHP](https://img.shields.io/badge/PHP-8.2+-777BB4?logo=php&logoColor=white)
![Laravel](https://img.shields.io/badge/Laravel-11-FF2D20?logo=laravel&logoColor=white)
![WooCommerce](https://img.shields.io/badge/WooCommerce-v3_REST_API-96588A?logo=woocommerce&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-tracking_local-003B57?logo=sqlite&logoColor=white)

---

## ¿Qué resuelve este proyecto?

El sistema de cupones nativo de WooCommerce tiene limitaciones conocidas que lo hacen inadecuado para plataformas de e-commerce en producción:

| Limitación de WooCommerce | Solución implementada |
|---------------------------|----------------------|
| Restricciones de categoría usan lógica AND — el producto debe pertenecer a **todas** las categorías | Resuelve categorías a IDs de producto y aplica lógica **OR** |
| El campo `email_restrictions` tiene bugs via REST API | Almacena el email localmente y valida en el servicio |
| El contador de usos tiene double-count bajo concurrencia | Tracking independiente en SQLite local |
| No hay creación masiva de cupones nativa | Endpoint bulk soporta hasta 500 cupones por request |

El microservicio actúa como intermediario entre el frontend/backoffice y WooCommerce: aplica reglas de negocio, sincroniza con WooCommerce via su API REST y lleva el conteo de usos localmente.

---

## Estructura del repositorio

```
coupon-management-microservice/
├── version-a/               # FastAPI (Python 3.11+) — implementación de referencia
├── version-b/               # Laravel 11 (PHP 8.2+)  — contrato idéntico
└── postman_collection.json  # 9 requests listos para importar
```

Ambas versiones exponen el **mismo contrato de API** — mismos endpoints, mismos shapes de request/response, mismas reglas de negocio. Solo difiere el stack de implementación.

---

## Inicio rápido

Cada versión es completamente autocontenida. Un solo comando levanta el stack completo:

```bash
# Version A — FastAPI
cd version-a
cp .env.example .env
docker compose up -d
# API disponible en http://localhost:8000/api/v1

# Version B — Laravel
cd version-b
cp .env.example .env
docker compose up -d
# API disponible en http://localhost:8001/api/v1
```

> **El primer arranque tarda 3–5 minutos.** El contenedor `wpcli` instala WordPress, activa WooCommerce, genera las API keys y carga los datos de ejemplo automáticamente. No se requiere intervención manual.

### Servicios Docker

| Servicio | Descripción |
|----------|-------------|
| `db` | MySQL 8.0 — base de datos de WordPress |
| `wordpress` | WordPress + WooCommerce (configurado automáticamente) |
| `wpcli` | Contenedor one-shot — instala WC y genera credenciales |
| `app` | El microservicio (carga las credenciales WC al arrancar) |

---

## Referencia de la API

**URL base:** `http://localhost:8000/api/v1` (version-a) / `http://localhost:8001/api/v1` (version-b)
**Autenticación:** header `X-API-Key: <valor>` (todos los endpoints excepto `/health`)

### Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `POST` | `/coupons` | Crear un cupón individual | Requerida |
| `POST` | `/coupons/bulk` | Creación masiva de hasta 500 cupones | Requerida |
| `GET` | `/coupons` | Listar cupones con filtros y paginación | Requerida |
| `GET` | `/coupons/{code}` | Obtener detalle de un cupón por código | Requerida |
| `PUT` | `/coupons/{code}` | Actualizar un cupón | Requerida |
| `DELETE` | `/coupons/{code}` | Soft delete de un cupón | Requerida |
| `POST` | `/coupons/{code}/validate` | Validar cupón sin registrar uso | Requerida |
| `POST` | `/coupons/{code}/apply` | Aplicar cupón — incrementa contador local | Requerida |
| `GET` | `/health` | Health check (DB + conectividad WooCommerce) | No |

### Envelope de respuesta

Todos los endpoints retornan la misma estructura:

```json
{
  "data": { ... },
  "meta": { "timestamp": "2025-03-10T20:00:00Z" },
  "error": null
}
```

### Ejemplo — Crear cupón

```bash
curl -s -X POST http://localhost:8000/api/v1/coupons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "type": "birthday",
    "discount_type": "percent",
    "amount": 99,
    "email": "cliente@ejemplo.com",
    "usage_limit": 1
  }' | jq .
# amount es forzado a 15 por la Regla 5
# expires_at es calculado como ahora+30d por la Regla 6
```

### Ejemplo — Creación masiva

```bash
curl -s -X POST http://localhost:8000/api/v1/coupons/bulk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "type": "campaign",
    "discount_type": "percent",
    "amount": 20,
    "quantity": 100,
    "prefix": "CYBER2025",
    "expires_at": "2025-12-31T23:59:00Z"
  }' | jq .
# Retorna: { "created": 100, "failed": 0, "errors": [] }
```

---

## Tipos de cupón

| Tipo | Descuento | Expiración | Stackable | Email obligatorio | Notas |
|------|-----------|------------|-----------|-------------------|-------|
| `birthday` | **15% fijo** | 30 días | No | Sí | El monto enviado siempre se sobreescribe |
| `gift_card` | Configurable | Máx 365 días | No | Sí | |
| `referral` | **$3.000 COP fijo** | 30 días | No | Sí (referido) | El monto enviado siempre se sobreescribe |
| `partner` | % según convenio | 90 días | No | No | `partner_code` obligatorio en el body |
| `night_sale` | Máx 50% | **24 horas** | No | No | `expiration_days` se ignora |
| `campaign` | % o fijo | `expires_at` explícito | **Sí** | No | `prefix` obligatorio |

### Patrones de generación de códigos

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| `birthday` | `BD-{RANDOM6}` | `BD-X7K2M9` |
| `gift_card` | `GC-{RANDOM8}` | `GC-A3B7C9D2` |
| `referral` | `REF-{RANDOM6}` | `REF-P4Q8R2` |
| `partner` | `{PARTNER_CODE}-{RANDOM4}` | `CNVN-A3B7` |
| `night_sale` | `NS-{YYYYMMDD}-{RANDOM4}` | `NS-20250315-K7M2` |
| `campaign` | `{PREFIX}-{RANDOM6}` | `CYBER2025-X7K2M9` |

La unicidad del código se verifica contra la base local **y** contra la API de WooCommerce antes de crear. En caso de colisión se reintenta hasta 3 veces.

---

## Reglas de negocio

### Regla 1 — Generación de códigos
Patrones específicos por tipo con caracteres alfanuméricos en mayúscula (A–Z, 0–9). Verificación de unicidad local + WooCommerce con hasta 3 reintentos.

### Regla 2 — Lógica OR en categorías
WooCommerce aplica AND a las restricciones de categoría. Este microservicio consulta `GET /wp-json/wc/v3/products?category={id}` por cada categoría, une los `product_ids` resultantes y los envía a WooCommerce en lugar de `product_categories`, logrando el comportamiento OR.

### Regla 3 — Tracking local de usos
Cada llamada a `/apply` incrementa un contador en la tabla local `CouponUsage`. El endpoint `/validate` consulta este contador, no el `usage_count` de WooCommerce (que puede duplicarse bajo concurrencia).

### Regla 4 — Workaround de restricción por email
El campo `email_restrictions` en la API de WooCommerce tiene bugs conocidos. Este microservicio almacena el email localmente y lo valida en `/validate` y `/apply` — nunca se envía a WooCommerce.

### Regla 5 — Validación de montos
- `birthday` → siempre 15%, el valor enviado se ignora
- `referral` → siempre $3.000 COP, el valor enviado se ignora
- `night_sale` → porcentaje máximo 50%
- Monto fijo → máximo `MAX_FIXED_DISCOUNT` (default: 500.000 COP)

### Regla 6 — Enforcement de expiración
- `birthday`, `referral` → siempre 30 días desde la creación
- `partner` → siempre 90 días desde la creación
- `night_sale` → siempre 24 horas, `expiration_days` se ignora
- `gift_card` → máximo 365 días
- `campaign` → requiere `expires_at` explícito, no acepta `expiration_days`

---

## Ejecución de tests

### Version A — pytest (10 tests)

```bash
# Dentro de Docker
docker compose exec app pytest tests/ -v

# Local (requiere venv)
cd version-a
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
API_KEY=test WC_BASE_URL=http://localhost \
  WC_CONSUMER_KEY=ck WC_CONSUMER_SECRET=cs \
  pytest tests/ -v
```

### Version B — PHPUnit (10 tests)

```bash
# Dentro de Docker
docker compose exec app php artisan test

# Local (requiere Composer + PHP 8.2)
cd version-b
composer install
php artisan test
```

Los 20 tests (10 por versión) cubren las 6 reglas de negocio sin llamadas HTTP reales — WooCommerce está mockeado en los tests unitarios.

---

## Arquitectura

```
HTTP Request
    │
    ▼
Middleware X-API-Key
    │
    ▼
Controller / Router
    │
    ▼
CouponService  ──────────────►  WooCommerceClient (HTTP)
    │                               WooCommerce v3 REST API
    │
    ▼
SQLite (tracking local)
  ├── Coupon         (code, type, amount, email, use_count, ...)
  └── CouponUsage    (coupon_id, used_at, context JSON)
```

### Archivos clave — Version A (FastAPI)

| Archivo | Responsabilidad |
|---------|----------------|
| `app/main.py` | 9 route handlers FastAPI |
| `app/service.py` | Implementación de las 6 reglas de negocio |
| `app/wc_client.py` | Cliente HTTP WooCommerce (httpx) |
| `app/code_generator.py` | Generador de códigos por tipo |
| `app/models.py` | Modelos ORM SQLAlchemy |
| `app/schemas.py` | Schemas Pydantic v2 request/response |

### Archivos clave — Version B (Laravel)

| Archivo | Responsabilidad |
|---------|----------------|
| `app/Http/Controllers/CouponController.php` | Route handlers |
| `app/Services/CouponService.php` | Implementación de las 6 reglas de negocio |
| `app/Services/WooCommerceClient.php` | Cliente HTTP WooCommerce (Guzzle) |
| `app/Services/CodeGenerator.php` | Generador de códigos por tipo |
| `app/Models/Coupon.php` | Modelo Eloquent |
| `routes/api.php` | Definición de rutas |

---

## Variables de entorno

```bash
# Requeridas
API_KEY=changeme                          # Valor del header X-API-Key
WC_BASE_URL=http://wordpress              # URL interna de WooCommerce
WC_CONSUMER_KEY=ck_xxx                   # Generada automáticamente por wpcli
WC_CONSUMER_SECRET=cs_xxx               # Generada automáticamente por wpcli

# Opcionales
MAX_FIXED_DISCOUNT=500000               # Descuento fijo máximo en COP (default: 500000)
DATABASE_URL=sqlite:///./coupons.db     # Ruta SQLite (version-a)
DB_DATABASE=/var/www/database/db.sqlite # Ruta SQLite (version-b)
```

Las credenciales de WooCommerce (`WC_CONSUMER_KEY`, `WC_CONSUMER_SECRET`) son **generadas automáticamente** por el contenedor `wpcli` en el primer arranque e inyectadas en el contenedor `app` vía `wc-credentials.env`. No se requiere configuración manual de credenciales.

---

## Decisiones técnicas

| Decisión | Justificación |
|----------|---------------|
| `email_restrictions` nunca se envía a WooCommerce | Bug conocido en la API de WC causa comportamiento inconsistente |
| SQLite local para tracking de usos | Desacoplado de WooCommerce — previene double-counting bajo concurrencia |
| `individual_use=true` para todos los tipos excepto `campaign` | Los cupones de campaña son explícitamente apilables |
| Solo soft delete (`deleted_at`) | Preserva el historial de auditoría; el `DELETE` mueve el cupón a la papelera de WC |
| `/validate` siempre retorna HTTP 200 | `valid: false` es una respuesta válida de negocio, no un error HTTP |
| `partner_code` en el body del request | No es variable de entorno — cada partner tiene un código distinto |
| Lookup de códigos case-insensitive | Evita inconsistencias entre `BD-X7K2M9` y `bd-x7k2m9` |

### Fixes de infraestructura no obvios

Problemas resueltos durante el desarrollo que pueden ser útiles si se despliega de forma independiente:

- **Redirects 301 de WordPress** — WP redirige `/coupons` → `/coupons/` (trailing slash). Resuelto con `follow_redirects=True` en httpx y trailing slashes explícitos en todas las URLs de Guzzle.
- **WooCommerce Basic Auth sobre HTTP** — WC solo permite Basic Auth sobre HTTPS por defecto. Resuelto con un must-use plugin (`mu-plugins/allow-http-basic-auth.php`) que establece `$_SERVER["HTTPS"] = "on"` para las rutas REST de WC.
- **Estructura de permalinks de WordPress** — La API REST de WC requiere la estructura `/%postname%/`. Configurada automáticamente por el script de setup.
- **Healthcheck de MySQL 8.0** — `mysqladmin ping` falla con la configuración TLS por defecto en MySQL 8. Resuelto con `--ssl=false` / `--ssl-mode=DISABLED`.

---

## Colección Postman

Importar `postman_collection.json` desde la raíz del repositorio. Configurar estas variables en el entorno de Postman:

| Variable | Valor |
|----------|-------|
| `baseUrl` | `http://localhost:8000/api/v1` (version-a) o `http://localhost:8001/api/v1` (version-b) |
| `apiKey` | `changeme` (o el valor configurado en `.env`) |

La colección incluye 9 requests preconfigurados que cubren todos los endpoints.

---

## Health check

```bash
curl -s http://localhost:8000/api/v1/health | jq .
```

```json
{
  "data": {
    "status": "ok",
    "checks": {
      "database": "ok",
      "woocommerce": "ok"
    }
  },
  "meta": { "timestamp": "2025-03-10T20:00:00Z" },
  "error": null
}
```

Retorna `503 Service Unavailable` si alguna dependencia no está disponible.

---

## Licencia

MIT
