<?php

namespace App\Http\Controllers;

use App\Http\Requests\{CreateCouponRequest, UpdateCouponRequest, ValidateCouponRequest, ApplyCouponRequest, BulkCouponRequest};
use App\Models\Coupon;
use App\Services\CouponService;
use Illuminate\Http\{JsonResponse, Request};

class CouponController extends Controller
{
    public function __construct(private CouponService $service) {}

    public function store(CreateCouponRequest $request): JsonResponse
    {
        try {
            $coupon = $this->service->create($request->validated());
            return $this->ok($coupon, 201);
        } catch (\InvalidArgumentException $e) {
            return $this->fail($e->getMessage(), 400);
        } catch (\Exception $e) {
            return $this->fail('Error interno al crear el cupón', 500);
        }
    }

    public function index(Request $request): JsonResponse
    {
        $filters  = $request->only(['type', 'status', 'email', 'code']);
        $perPage  = min((int) $request->get('per_page', 20), 100);
        $page     = (int) $request->get('page', 1);

        $query = Coupon::query();
        foreach ($filters as $field => $value) {
            if (!$value) continue;
            if ($field === 'code') {
                $query->where('code', 'like', "%{$value}%");
            } elseif ($field === 'email') {
                $query->where('allowed_email', $value);
            } else {
                $query->where($field, $value);
            }
        }

        $paginated = $query->paginate($perPage, ['*'], 'page', $page);
        return $this->ok($paginated->items(), 200, [
            'total'        => $paginated->total(),
            'per_page'     => $perPage,
            'current_page' => $page,
            'last_page'    => $paginated->lastPage(),
        ]);
    }

    public function show(string $code): JsonResponse
    {
        $code = strtoupper($code);
        $coupon = Coupon::where('code', $code)->first();
        if (!$coupon) return $this->fail('Cupón no encontrado', 404);
        return $this->ok($coupon);
    }

    public function update(UpdateCouponRequest $request, string $code): JsonResponse
    {
        $code = strtoupper($code);
        $coupon = Coupon::where('code', $code)->whereNull('deleted_at')->first();
        if (!$coupon) return $this->fail('Cupón no encontrado', 404);
        try {
            $coupon = $this->service->update($coupon, $request->validated());
            return $this->ok($coupon);
        } catch (\InvalidArgumentException $e) {
            return $this->fail($e->getMessage(), 400);
        } catch (\Exception $e) {
            return $this->fail('Error interno al actualizar el cupón', 500);
        }
    }

    public function destroy(string $code): JsonResponse
    {
        $code = strtoupper($code);
        $coupon = Coupon::where('code', $code)->whereNull('deleted_at')->first();
        if (!$coupon) return $this->fail('Cupón no encontrado', 404);

        try {
            if ($coupon->wc_id) {
                $this->service->wc->trashCoupon($coupon->wc_id);
            }
        } catch (\Exception $e) {
            // Si WC falla, el soft delete local igual se guarda
        }

        $coupon->status = 'deleted';
        $coupon->save();
        $coupon->delete(); // SoftDeletes — setea deleted_at

        return $this->ok(['code' => $coupon->code, 'deleted_at' => $coupon->deleted_at?->toIso8601String()]);
    }

    public function validateCoupon(ValidateCouponRequest $request, string $code): JsonResponse
    {
        $code = strtoupper($code);
        $coupon = Coupon::where('code', $code)->first();
        if (!$coupon) return $this->fail('Cupón no encontrado', 404);

        $result = $this->service->validate(
            $coupon,
            $request->validated('email'),
            $request->validated('product_ids', [])
        );
        return $this->ok($result);
    }

    public function apply(ApplyCouponRequest $request, string $code): JsonResponse
    {
        $code = strtoupper($code);
        $coupon = Coupon::where('code', $code)->whereNull('deleted_at')->first();
        if (!$coupon) return $this->fail('Cupón no encontrado', 404);
        try {
            $coupon = $this->service->apply($coupon, $request->email, $request->order_id);
            return $this->ok([
                'code'        => $coupon->code,
                'use_count'   => $coupon->use_count,
                'usage_limit' => $coupon->usage_limit,
                'applied_at'  => now()->toIso8601String(),
            ]);
        } catch (\InvalidArgumentException $e) {
            return $this->fail($e->getMessage(), 422);
        } catch (\Exception $e) {
            return $this->fail('Error interno al aplicar el cupón', 500);
        }
    }

    public function bulk(BulkCouponRequest $request): JsonResponse
    {
        try {
            $result = $this->service->createBulk($request->validated());
            return $this->ok($result);
        } catch (\Exception $e) {
            return $this->fail('Error interno al procesar el lote', 500);
        }
    }

    private function ok(mixed $data, int $status = 200, array $meta = []): JsonResponse
    {
        return response()->json([
            'data'  => $data,
            'meta'  => array_merge(['timestamp' => now()->toIso8601String()], $meta),
            'error' => null,
        ], $status);
    }

    private function fail(string $message, int $status): JsonResponse
    {
        return response()->json([
            'data'  => null,
            'meta'  => ['timestamp' => now()->toIso8601String()],
            'error' => $message,
        ], $status);
    }
}
