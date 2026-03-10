<?php

namespace App\Services;

use App\Contracts\WooCommerceClientInterface;
use App\Logging\CouponLogger;
use App\Models\Coupon;
use App\Models\CouponUsage;
use Carbon\Carbon;
use Illuminate\Support\Facades\DB;

class CouponService
{
    public function __construct(
        public WooCommerceClientInterface $wc,
        private CodeGenerator $codeGen
    ) {}

    public function create(array $input): Coupon
    {
        $startTime = microtime(true);
        $type = $input['type'];

        if ($type === 'partner' && empty($input['partner_code'])) {
            throw new \InvalidArgumentException("El campo 'partner_code' es obligatorio para tipo partner");
        }
        if ($type === 'campaign' && empty($input['prefix'])) {
            throw new \InvalidArgumentException("El campo 'prefix' es obligatorio para tipo campaign");
        }
        if (in_array($type, ['birthday', 'gift_card', 'referral']) && empty($input['email'])) {
            throw new \InvalidArgumentException("El campo 'email' es obligatorio para tipo {$type}");
        }

        $amount  = $this->enforceAmount($type, $input['discount_type'], (float) $input['amount']);
        $expires = $this->calculateExpiration(
            $type,
            $input['expiration_days'] ?? null,
            isset($input['expires_at']) ? Carbon::parse($input['expires_at']) : null
        );

        $code = $this->codeGen->generateUnique($type, [
            'prefix'       => $input['prefix'] ?? null,
            'partner_code' => $input['partner_code'] ?? null,
        ]);

        $productIds = $this->resolveCategoryProducts($input['categories'] ?? []);
        $productIds = array_unique(array_merge($productIds, $input['products'] ?? []));

        // Nota: NO incluir email_restrictions — WooCommerce tiene bugs conocidos con este campo.
        // La restricción de email se almacena localmente en allowed_email y se valida en /validate.
        $wcPayload = [
            'code'           => $code,
            'discount_type'  => $input['discount_type'],
            'amount'         => (string) $amount,
            'date_expires'   => $expires->format('Y-m-d\TH:i:s'),
            'usage_limit'    => $input['usage_limit'] ?? null,
            'individual_use' => $type !== 'campaign',  // campaign es stackable
            'product_ids'    => array_values($productIds),
        ];

        $wcCoupon = $this->wc->createCoupon($wcPayload);

        $coupon = Coupon::create([
            'wc_id'         => $wcCoupon['id'],
            'code'          => $code,
            'type'          => $type,
            'discount_type' => $input['discount_type'],
            'amount'        => $amount,
            'allowed_email' => $input['email'] ?? null,
            'usage_limit'   => $input['usage_limit'] ?? null,
            'expires_at'    => $expires,
            'categories'    => $input['categories'] ?? [],
            'meta'          => ['restricted_product_ids' => array_values($productIds)],
        ]);

        $durationMs = (int) ((microtime(true) - $startTime) * 1000);
        CouponLogger::couponCreated($code, $type, $amount, $wcCoupon['id'] ?? null, $durationMs);

        return $coupon;
    }

    public function enforceAmount(string $type, string $discountType, float $amount): float
    {
        if ($type === 'birthday') return 15.0;
        if ($type === 'referral') return 3000.0;
        if ($type === 'night_sale' && $amount > 50) return 50.0;
        if ($discountType === 'percent' && $amount > 100) return 100.0;
        if ($discountType !== 'percent' && $amount > config('app.max_fixed_discount')) {
            return (float) config('app.max_fixed_discount');
        }
        return $amount;
    }

    public function calculateExpiration(string $type, ?int $days, ?Carbon $explicit): Carbon
    {
        return match ($type) {
            'birthday', 'referral' => now()->addDays(30),
            'partner'              => now()->addDays(90),
            'night_sale'           => now()->addHours(24),
            'gift_card'            => now()->addDays(min($days ?? 365, 365)),
            'campaign'             => $explicit
                ?? throw new \InvalidArgumentException(
                    "El tipo 'campaign' requiere una fecha de expiración explícita en 'expires_at'"
                ),
            default => now()->addDays($days ?? 30),
        };
    }

    private function resolveCategoryProducts(array $categoryIds): array
    {
        if (empty($categoryIds)) return [];

        // WooCommerce aplica AND entre categorías cuando se pasan como filtro de cupón.
        // Para obtener comportamiento OR, resolvemos cada categoría a product_ids
        // y enviamos el conjunto unificado como product_ids al cupón.
        $productIds = [];
        foreach ($categoryIds as $catId) {
            $ids        = $this->wc->getProductsByCategory($catId);
            $productIds = array_merge($productIds, $ids);
        }
        return array_unique($productIds);
    }

    public function validate(Coupon $coupon, string $email, array $productIds): array
    {
        $reasons = [];

        if ($coupon->trashed() || $coupon->status === 'deleted') {
            $reasons[] = 'El cupón ha sido eliminado';
        }
        if ($coupon->isExpired()) {
            $reasons[] = 'El cupón ha expirado';
        }
        if ($coupon->hasReachedLimit()) {
            $reasons[] = 'El cupón ha alcanzado su límite de usos';
        }
        // Regla 4: validamos email localmente (no en WC que tiene bugs con email_restrictions)
        if ($coupon->allowed_email && strtolower($coupon->allowed_email) !== strtolower($email)) {
            $reasons[] = 'El email no corresponde al cupón';
        }
        if (!empty($productIds) && !empty($coupon->meta['restricted_product_ids'] ?? [])) {
            $restricted = $coupon->meta['restricted_product_ids'];
            if (empty(array_intersect($productIds, $restricted))) {
                $reasons[] = 'Ningún producto del carrito aplica para este cupón';
            }
        }

        return ['valid' => empty($reasons), 'reasons' => $reasons];
    }

    public function apply(Coupon $coupon, string $email, ?string $orderId): Coupon
    {
        $validation = $this->validate($coupon, $email, []);
        if (!$validation['valid']) {
            CouponLogger::validationFailed($coupon->code, $validation['reasons']);
            throw new \InvalidArgumentException(implode('; ', $validation['reasons']));
        }

        DB::transaction(function () use ($coupon, $email, $orderId) {
            CouponUsage::create([
                'coupon_id' => $coupon->id,
                'email'     => $email,
                'order_id'  => $orderId,
                'used_at'   => now(),
            ]);
            $coupon->increment('use_count');
        });

        $coupon = $coupon->fresh();
        CouponLogger::couponApplied($coupon->code, $email, $orderId, $coupon->use_count);

        return $coupon;
    }

    public function update(Coupon $coupon, array $data): Coupon
    {
        $inmutables = array_intersect(array_keys($data), ['code', 'type', 'discount_type']);
        if (!empty($inmutables)) {
            throw new \InvalidArgumentException(
                'Los campos ' . implode(', ', $inmutables) . ' son inmutables'
            );
        }

        if (isset($data['amount'])) {
            $data['amount'] = $this->enforceAmount($coupon->type, $coupon->discount_type, (float) $data['amount']);
        }
        if (isset($data['email'])) {
            $data['allowed_email'] = $data['email'];
            unset($data['email']);
        }

        $coupon->fill($data)->save();

        if ($coupon->wc_id) {
            $wcUpdate = array_filter([
                'amount'       => isset($data['amount']) ? (string) $coupon->amount : null,
                'date_expires' => isset($data['expires_at']) ? $coupon->expires_at?->format('Y-m-d\TH:i:s') : null,
                'usage_limit'  => $data['usage_limit'] ?? null,
            ]);
            if (!empty($wcUpdate)) {
                $this->wc->updateCoupon($coupon->wc_id, $wcUpdate);
            }
        }

        return $coupon->fresh();
    }

    public function createBulk(array $input): array
    {
        $quantity = $input['quantity'];
        $created  = 0;
        $failed   = 0;
        $errors   = [];

        $batchSize = 20;
        for ($i = 0; $i < $quantity; $i += $batchSize) {
            $batch = min($batchSize, $quantity - $i);
            for ($j = 0; $j < $batch; $j++) {
                try {
                    $this->create($input);
                    $created++;
                } catch (\Exception $e) {
                    $failed++;
                    $errors[] = $e->getMessage();
                }
            }
        }

        CouponLogger::bulkOperation($quantity, $created, $failed);

        return ['created' => $created, 'failed' => $failed, 'errors' => $errors];
    }
}
