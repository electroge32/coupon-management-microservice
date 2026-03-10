# ADIPA Coupon Service — Version A (FastAPI)

Microservicio de gestión de cupones con integración a WooCommerce.

## Requisitos

- Docker + Docker Compose
- (para desarrollo local) Python 3.11+

## Inicio rápido

```bash
cd version-a
cp .env.example .env
# Editar .env con tus valores
docker compose up -d
```

> **Nota:** El primer arranque instala WooCommerce automáticamente (~3-5 min).

## Variables de entorno (.env)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `API_KEY` | Clave para autenticación de requests | `sk_adipa_2024` |
| `WC_BASE_URL` | URL base de la tienda WooCommerce | `http://wordpress:80` |
| `WC_CONSUMER_KEY` | Consumer Key de WooCommerce REST API | `ck_xxx` |
| `WC_CONSUMER_SECRET` | Consumer Secret de WooCommerce REST API | `cs_xxx` |
| `MAX_FIXED_DISCOUNT` | Descuento fijo máximo permitido (COP) | `500000` |
| `DATABASE_URL` | Ruta de SQLite | `sqlite:///./coupons.db` |

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
| `partner` | Porcentaje libre | 90 días | `partner_code` requerido en el body |
| `night_sale` | Máx 50% | 24 horas | Ignora `expiration_days` |
| `campaign` | Stackable | Requiere `expires_at` | Varios cupones acumulables |

## Formato de respuesta

```json
{
  "data": {},
  "meta": { "timestamp": "2024-01-15T10:30:00Z" },
  "error": null
}
```

## Tests

```bash
cd version-a
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
API_KEY=test WC_BASE_URL=http://localhost WC_CONSUMER_KEY=ck WC_CONSUMER_SECRET=cs pytest tests/ -v
```

10 tests cubriendo las 6 reglas de negocio. Sin llamadas HTTP reales (WooCommerce mockeado).

## Arquitectura

FastAPI → CouponService → WooCommerceClient (httpx síncrono) + SQLite local vía SQLAlchemy.

**Decisión clave:** `email_restrictions` no se envía a WooCommerce (bugs conocidos en WC) — se valida localmente antes de aplicar el cupón.
