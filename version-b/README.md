# ADIPA Coupon Service — Version B (Laravel)

Microservicio de gestión de cupones con integración a WooCommerce.

## Requisitos

- Docker + Docker Compose
- (para desarrollo local) PHP 8.2+, Composer

## Inicio rápido

```bash
cd version-b
cp .env.example .env
# Editar .env con tus valores
docker compose up -d
```

> **Nota:** El primer arranque ejecuta migraciones automáticamente.

## Puertos

| Servicio | URL |
|----------|-----|
| Laravel API | `http://localhost:8001/api/v1` |
| WordPress admin | `http://localhost:8081/wp-admin` (usuario: `admin` / contraseña: `admin123`) |

> No requiere entrada en `/etc/hosts`. El `siteurl` de WordPress está configurado a `http://localhost:8081` para acceso directo desde el browser. Internamente, el microservicio se comunica con WooCommerce vía `http://wordpress` (DNS de Docker).

## Variables de entorno (.env)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| APP_KEY | Clave de aplicación Laravel | `base64:xxx` |
| APP_ENV | Entorno (local/production) | `local` |
| APP_DEBUG | Modo debug | `true` |
| API_KEY | Clave para autenticación de requests | `sk_adipa_2024` |
| WC_BASE_URL | URL base de la tienda WooCommerce | `https://tienda.com` |
| WC_CONSUMER_KEY | Consumer Key de WooCommerce REST API | `ck_xxx` |
| WC_CONSUMER_SECRET | Consumer Secret de WooCommerce REST API | `cs_xxx` |
| MAX_FIXED_DISCOUNT | Descuento fijo máximo permitido (COP) | `50000` |
| DB_DATABASE | Ruta de SQLite | `/var/www/database/database.sqlite` |

## Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/coupons` | Crear cupón individual | API Key |
| POST | `/api/v1/coupons/bulk` | Crear cupones en batch | API Key |
| GET | `/api/v1/coupons` | Listar cupones con filtros | API Key |
| GET | `/api/v1/coupons/{code}` | Obtener cupón por código | API Key |
| PUT | `/api/v1/coupons/{code}` | Actualizar cupón | API Key |
| DELETE | `/api/v1/coupons/{code}` | Eliminar cupón (soft delete) | API Key |
| POST | `/api/v1/coupons/{code}/validate` | Validar cupón para uso | API Key |
| POST | `/api/v1/coupons/{code}/apply` | Aplicar cupón (incrementa contador) | API Key |
| GET | `/api/v1/health` | Health check del servicio | — |

## Autenticación

Header requerido en todas las peticiones (excepto health):

```
X-API-Key: <valor>
```

Sin header → `401 Unauthorized`.

## Tipos de cupón

| Tipo | Descuento | Expiración | Notas |
|------|-----------|------------|-------|
| `birthday` | 15% fijo | 30 días | Ignora monto enviado |
| `gift_card` | Libre | 365 días | Monto definido por admin |
| `referral` | 3000 COP fijo | 30 días | Ignora monto enviado |
| `partner` | Porcentaje libre | 90 días | Define % según convenio |
| `night_sale` | Máx 50% | 24 horas | Ignora `expiration_days` |
| `campaign` | Stackable | Requiere `expires_at` | Varios cupones acumulables |

## Formato de respuesta

```json
{
  "data": {},
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "error": null
}
```

## Tests

```bash
docker compose exec app php artisan test
```

10 tests cubriendo las 6 reglas de negocio.

## Arquitectura

Laravel 11 → CouponService → WooCommerceClient (Guzzle) + SQLite vía Eloquent.

**Decisiones técnicas:**
- `email_restrictions` no se envía a WooCommerce (bugs conocidos en WC) — se valida localmente.
- Todas las URLs del cliente WC incluyen trailing slash (`/wp-json/wc/v3/coupons/`) para evitar redirects 301 de WordPress.
- Guzzle configurado con `allow_redirects: false` — la comunicación interna es directa vía `http://wordpress` (DNS Docker, puerto 80 del contenedor).
- Lookup de cupones es case-insensitive via `strtoupper()` en el controller.
