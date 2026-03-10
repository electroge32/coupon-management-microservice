<?php

namespace App\Contracts;

interface WooCommerceClientInterface
{
    public function createCoupon(array $data): array;
    public function updateCoupon(int $wcId, array $data): array;
    public function trashCoupon(int $wcId): array;
    public function findCouponByCode(string $code): ?array;
    public function getProductsByCategory(int $categoryId): array;
    public function ping(): bool;
}
