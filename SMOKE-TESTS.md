# Smoke Tests End-to-End

Verificación integral del sistema en entorno Docker.

## Pre-requisitos

```bash
# 1. Levantar el stack completo (versión A o B)
cd version-a  # o version-b
docker compose up -d

# 2. Esperar a que WooCommerce esté listo (~2-3 minutos)
curl http://localhost:8000/api/v1/health

# version-b
curl http://localhost:8001/api/v1/health
```

## Ejecución

### Versión A (FastAPI)

```bash
cd version-a

# Vía Docker (recomendado)
docker compose exec app python tests/smoke_test.py

# Local (requiere venv)
pip install -r requirements.txt
python tests/smoke_test.py
```

### Versión B (Laravel)

```bash
cd version-b

# Vía Docker (recomendado)
docker compose exec app bash -c "API_KEY=changeme ./tests/smoke_test.sh"

# Local
./tests/smoke_test.sh
```

## Casos Cubiertos

| ID | Test | Verificación |
|----|------|--------------|
| T1 | Health Check | `GET /health` retorna `status: ok` |
| T2 | Auth Rejection | Sin `X-API-Key` retorna 401 |
| T3 | Birthday Creation | Amount 99 → forzado a 15 (Regla 5) |
| T4 | Referral Creation | Amount 9999 → forzado a 3000 (Regla 5) |
| T5 | Wrong Email | Validación falla con email incorrecto (Regla 4) |
| T6 | Validate & Apply | Flujo completo de aplicación |
| T7 | Campaign Validation | Sin `expires_at` retorna 400 |
| T8 | Campaign Creation | Con `expires_at` crea exitosamente |
| T9 | List Coupons | Paginación y filtros funcionan |
| T10 | Bulk Creation | Creación de 3 cupones en lote |

## Verificación de Logs

### Versión A
```bash
docker compose logs -f app | grep -E 'coupon\.|woocommerce\.'
```

### Versión B
```bash
docker compose exec app tail -f storage/logs/coupons.log
```

Ejemplo de log esperado:
```json
{
  "timestamp": "2026-03-08T20:00:00.123Z",
  "level": "info",
  "action": "coupon.created",
  "coupon_code": "BD-X7K2M9",
  "type": "birthday",
  "amount": 15.0,
  "wc_id": 123,
  "duration_ms": 142
}
```

## Criterios de Éxito

- Los 10 smoke tests pasan sin errores
- Logs JSON estructurados se generan por cada operación
- Montos forzados correctamente (birthday=15%, referral=3000 COP)
- Validaciones de email funcionan independientemente de WooCommerce
- No hay errores 500 en ningún endpoint

## Troubleshooting

```bash
# Verificar estado de contenedores
docker compose ps

# Ver logs de la aplicación
docker compose logs app

# Verificar credenciales WC cargadas
docker compose exec app sh -c 'cat /proc/1/environ | tr "\0" "\n" | grep WC_'
```
