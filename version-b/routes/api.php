<?php

use App\Http\Controllers\{CouponController, HealthController};
use Illuminate\Support\Facades\Route;

Route::prefix('v1/coupons')
    ->middleware('api.key')
    ->group(function () {
        Route::get('/',                     [CouponController::class, 'index']);
        Route::post('/',                    [CouponController::class, 'store']);
        Route::post('/bulk',                [CouponController::class, 'bulk']);
        Route::get('/{code}',              [CouponController::class, 'show']);
        Route::put('/{code}',              [CouponController::class, 'update']);
        Route::delete('/{code}',           [CouponController::class, 'destroy']);
        Route::post('/{code}/validate',    [CouponController::class, 'validateCoupon']);
        Route::post('/{code}/apply',       [CouponController::class, 'apply']);
    });

Route::get('/v1/health', [HealthController::class, 'check']);
