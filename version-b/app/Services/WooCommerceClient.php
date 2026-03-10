<?php

namespace App\Services;

use App\Contracts\WooCommerceClientInterface;
use App\Logging\CouponLogger;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\RequestException;

class WooCommerceClient implements WooCommerceClientInterface
{
    private Client $client;
    private string $baseUrl;

    public function __construct()
    {
        $config = config('woocommerce');

        $this->baseUrl = rtrim($config['base_url'], '/');

        $this->client = new Client([
            'auth'            => [$config['consumer_key'], $config['consumer_secret']],
            'allow_redirects' => false, // todas las URLs incluyen trailing slash — no hay 301
            'headers'         => [
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ],
        ]);
    }

    public function createCoupon(array $data): array
    {
        try {
            $response = $this->client->post(
                $this->baseUrl . '/wp-json/wc/v3/coupons/',
                ['json' => $data]
            );

            return json_decode($response->getBody()->getContents(), true);
        } catch (RequestException $e) {
            CouponLogger::wcError(
                'POST /coupons',
                $e->getMessage(),
                $e->getResponse()?->getStatusCode()
            );
            throw $e;
        }
    }

    public function updateCoupon(int $wcId, array $data): array
    {
        try {
            $response = $this->client->put(
                $this->baseUrl . '/wp-json/wc/v3/coupons/' . $wcId . '/',
                ['json' => $data]
            );

            return json_decode($response->getBody()->getContents(), true);
        } catch (RequestException $e) {
            CouponLogger::wcError(
                'PUT /coupons/' . $wcId,
                $e->getMessage(),
                $e->getResponse()?->getStatusCode()
            );
            throw $e;
        }
    }

    public function trashCoupon(int $wcId): array
    {
        try {
            $response = $this->client->delete(
                $this->baseUrl . '/wp-json/wc/v3/coupons/' . $wcId . '/',
                ['query' => ['force' => 'false']]
            );

            return json_decode($response->getBody()->getContents(), true);
        } catch (RequestException $e) {
            CouponLogger::wcError(
                'DELETE /coupons/' . $wcId,
                $e->getMessage(),
                $e->getResponse()?->getStatusCode()
            );
            throw $e;
        }
    }

    public function findCouponByCode(string $code): ?array
    {
        $response = $this->client->get(
            $this->baseUrl . '/wp-json/wc/v3/coupons/',
            ['query' => ['code' => $code]]
        );

        $data = json_decode($response->getBody()->getContents(), true);

        if (empty($data)) {
            return null;
        }

        return $data[0];
    }

    public function getProductsByCategory(int $categoryId): array
    {
        $response = $this->client->get(
            $this->baseUrl . '/wp-json/wc/v3/products/',
            ['query' => ['category' => $categoryId, 'per_page' => 100]]
        );

        $products = json_decode($response->getBody()->getContents(), true);

        return array_column($products, 'id');
    }

    public function ping(): bool
    {
        try {
            $this->client->get($this->baseUrl . '/wp-json/wc/v3/', [
                'timeout' => 3,
            ]);
            return true;
        } catch (\Throwable $e) {
            return false;
        }
    }
}
