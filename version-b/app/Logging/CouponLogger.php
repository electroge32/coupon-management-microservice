<?php

declare(strict_types=1);

namespace App\Logging;

use Illuminate\Support\Facades\Log;
use Monolog\Formatter\JsonFormatter;

/**
 * Structured JSON Logger para eventos de cupones.
 * 
 * Logs en formato JSON con campos trazables para auditoría y debugging.
 */
class CouponLogger
{
    private const CHANNEL = 'coupons';
    
    /**
     * Configura el canal de logs si no está configurado.
     */
    public static function configure(): void
    {
        if (!config('logging.channels.' . self::CHANNEL)) {
            config(['logging.channels.' . self::CHANNEL => [
                'driver' => 'single',
                'path' => storage_path('logs/coupons.log'),
                'level' => 'debug',
                'formatter' => JsonFormatter::class,
            ]]);
        }
    }
    
    /**
     * Log JSON estructurado con action y metadata.
     */
    private static function log(string $level, string $action, array $context = []): void
    {
        self::configure();
        
        $payload = array_merge([
            'timestamp' => now()->toIso8601String(),
            'level' => $level,
            'action' => $action,
        ], $context);
        
        Log::channel(self::CHANNEL)->{$level}('', $payload);
    }
    
    /**
     * Cupón creado exitosamente.
     */
    public static function couponCreated(
        string $code,
        string $type,
        float $amount,
        ?int $wcId,
        int $durationMs
    ): void {
        self::log('info', 'coupon.created', [
            'coupon_code' => $code,
            'type' => $type,
            'amount' => $amount,
            'wc_id' => $wcId,
            'duration_ms' => $durationMs,
        ]);
    }
    
    /**
     * Cupón aplicado a una orden.
     */
    public static function couponApplied(
        string $code,
        string $email,
        ?string $orderId,
        int $useCount
    ): void {
        self::log('info', 'coupon.applied', [
            'coupon_code' => $code,
            'email' => $email,
            'order_id' => $orderId,
            'use_count' => $useCount,
        ]);
    }
    
    /**
     * Validación de cupón fallida.
     */
    public static function validationFailed(string $code, array $reasons): void
    {
        self::log('info', 'coupon.validation_failed', [
            'coupon_code' => $code,
            'reasons' => $reasons,
        ]);
    }
    
    /**
     * Error en llamada a WooCommerce.
     */
    public static function wcError(
        string $endpoint,
        string $errorMessage,
        ?int $statusCode = null
    ): void {
        self::log('error', 'woocommerce.error', [
            'wc_endpoint' => $endpoint,
            'error_message' => $errorMessage,
            'status_code' => $statusCode,
        ]);
    }
    
    /**
     * Colisión de código detectada, se reintenta.
     */
    public static function codeCollision(
        string $codeAttempt,
        string $type,
        int $attemptNumber
    ): void {
        self::log('warning', 'code.collision', [
            'code_attempt' => $codeAttempt,
            'type' => $type,
            'attempt_number' => $attemptNumber,
        ]);
    }
    
    /**
     * Operación bulk completada.
     */
    public static function bulkOperation(int $quantity, int $created, int $failed): void
    {
        self::log('info', 'coupon.bulk_created', [
            'quantity' => $quantity,
            'created' => $created,
            'failed' => $failed,
        ]);
    }
}
