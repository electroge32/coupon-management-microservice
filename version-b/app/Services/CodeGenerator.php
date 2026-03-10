<?php

namespace App\Services;

use App\Contracts\WooCommerceClientInterface;
use App\Logging\CouponLogger;
use App\Models\Coupon;

class CodeGenerator
{
    private const CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

    public function __construct(
        private WooCommerceClientInterface $wc
    ) {}

    public function generate(string $type, array $options = []): string
    {
        $today = date('Ymd');

        return match ($type) {
            'birthday'   => 'BD-' . $this->random(6),
            'gift_card'  => 'GC-' . $this->random(8),
            'referral'   => 'REF-' . $this->random(6),
            // partner_code viene del body del request — valor libre, obligatorio para tipo partner
            'partner'    => ($options['partner_code'] ?? throw new \InvalidArgumentException("El campo 'partner_code' es obligatorio para tipo partner")) . '-' . $this->random(4),
            'night_sale' => 'NS-' . $today . '-' . $this->random(4),
            'campaign'   => ($options['prefix'] ?? 'CAMP') . '-' . $this->random(6),
            default      => throw new \InvalidArgumentException("Tipo de cupón desconocido: {$type}"),
        };
    }

    public function generateUnique(string $type, array $options = []): string
    {
        for ($attempt = 1; $attempt <= 3; $attempt++) {
            $code = $this->generate($type, $options);
            $existsLocal = $this->existsLocally($code);
            $existsWc = $this->existsInWc($code);
            
            if (!$existsLocal && !$existsWc) {
                return $code;
            }
            
            // Loggear colisión para trazabilidad
            CouponLogger::codeCollision($code, $type, $attempt);
        }
        throw new \RuntimeException(
            "No se pudo generar código único para tipo '{$type}' en 3 intentos"
        );
    }

    private function existsLocally(string $code): bool
    {
        return Coupon::where('code', $code)->exists();
    }

    private function existsInWc(string $code): bool
    {
        return $this->wc->findCouponByCode($code) !== null;
    }

    private function random(int $length): string
    {
        $charset = self::CHARSET;
        $max     = strlen($charset) - 1;
        $result  = '';
        for ($i = 0; $i < $length; $i++) {
            $result .= $charset[random_int(0, $max)];
        }
        return $result;
    }
}
