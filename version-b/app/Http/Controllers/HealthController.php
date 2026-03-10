<?php

namespace App\Http\Controllers;

use App\Contracts\WooCommerceClientInterface;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

class HealthController extends Controller
{
    public function __construct(private WooCommerceClientInterface $wc) {}

    public function check(): JsonResponse
    {
        $dbOk = true;
        try {
            DB::connection()->getPdo();
        } catch (\Exception $e) {
            $dbOk = false;
        }

        $wcOk = $this->wc->ping();

        $allOk      = $dbOk && $wcOk;
        $httpStatus = $allOk ? 200 : 503;

        return response()->json([
            'data'  => [
                'status'  => $allOk ? 'ok' : 'degraded',
                'version' => '1.0.0',
                'checks'  => [
                    'database'    => $dbOk ? 'ok' : 'error',
                    'woocommerce' => $wcOk ? 'ok' : 'error',
                ],
            ],
            'meta'  => ['timestamp' => now()->toIso8601String()],
            'error' => null,
        ], $httpStatus);
    }
}
