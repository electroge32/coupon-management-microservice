<?php

namespace Tests\Unit;

use Mockery;
use Illuminate\Foundation\Testing\RefreshDatabase;
use App\Services\CouponService;
use App\Services\CodeGenerator;
use App\Contracts\WooCommerceClientInterface;
use Tests\TestCase;

class CouponRulesTest extends TestCase
{
    use RefreshDatabase;

    protected $wc;
    protected $service;

    protected function setUp(): void
    {
        parent::setUp();

        config(['database.default' => 'sqlite', 'database.connections.sqlite.database' => ':memory:']);

        $this->wc = Mockery::mock(WooCommerceClientInterface::class);
        $this->wc->shouldReceive('findCouponByCode')->andReturn(null);
        $this->wc->shouldReceive('createCoupon')->andReturn(['id' => 999]);
        $this->wc->shouldReceive('getProductsByCategory')->andReturn([101, 102]);
        $this->wc->shouldReceive('trashCoupon')->andReturn(['id' => 999, 'status' => 'trash']);

        $codeGen = new CodeGenerator($this->wc);
        $this->service = new CouponService($this->wc, $codeGen);
    }

    protected function tearDown(): void
    {
        Mockery::close();
        parent::tearDown();
    }

    public function test_birthday_amount_is_always_15_percent(): void
    {
        $coupon = $this->service->create([
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 99,
            'email'         => 'owner@example.com',
        ]);

        $this->assertEquals(15.0, $coupon->amount, 'El monto birthday debe ser 15');
    }

    public function test_referral_amount_is_always_3000(): void
    {
        $coupon = $this->service->create([
            'type'          => 'referral',
            'discount_type' => 'fixed_cart',
            'amount'        => 9999,
            'email'         => 'ref@example.com',
        ]);

        $this->assertEquals(3000.0, $coupon->amount, 'El monto referral debe ser 3000');
    }

    public function test_validate_fails_with_wrong_email(): void
    {
        $coupon = $this->service->create([
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 50,
            'email'         => 'owner@example.com',
        ]);

        $result = $this->service->validate($coupon, 'otro@example.com', []);

        $this->assertFalse($result['valid']);
        $this->assertStringContainsStringIgnoringCase('email', implode(' ', $result['reasons']));
    }

    public function test_validate_fails_when_usage_limit_reached(): void
    {
        $coupon = $this->service->create([
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 50,
            'email'         => 'test@test.com',
            'usage_limit'   => 1,
        ]);

        $coupon->use_count = 1;
        $coupon->save();

        $result = $this->service->validate($coupon, 'test@test.com', []);

        $this->assertFalse($result['valid']);
    }

    public function test_campaign_requires_explicit_expiration(): void
    {
        $this->expectException(\InvalidArgumentException::class);

        $this->service->create([
            'type'          => 'campaign',
            'discount_type' => 'percent',
            'amount'        => 15,
            'prefix'        => 'PROMO',
        ]);
    }

    public function test_code_generator_retries_on_collision(): void
    {
        $this->wc = Mockery::mock(WooCommerceClientInterface::class);
        $this->wc->shouldReceive('findCouponByCode')
            ->once()
            ->andReturn(['id' => 1]);
        $this->wc->shouldReceive('findCouponByCode')
            ->andReturn(null);
        $this->wc->shouldReceive('createCoupon')->andReturn(['id' => 999]);

        $codeGen = new CodeGenerator($this->wc);
        $this->service = new CouponService($this->wc, $codeGen);

        $code = $codeGen->generateUnique('birthday', []);

        $this->assertStringStartsWith('BD-', $code);
    }

    public function test_category_or_logic_calls_wc_for_each_category(): void
    {
        $this->wc = Mockery::mock(WooCommerceClientInterface::class);
        $this->wc->shouldReceive('findCouponByCode')->andReturn(null);
        $this->wc->shouldReceive('createCoupon')->andReturn(['id' => 999]);
        $this->wc->shouldReceive('getProductsByCategory')->with(31)->once()->andReturn([101]);
        $this->wc->shouldReceive('getProductsByCategory')->with(67)->once()->andReturn([102]);
        $this->wc->shouldReceive('trashCoupon')->andReturn(['id' => 999, 'status' => 'trash']);

        $codeGen = new CodeGenerator($this->wc);
        $this->service = new CouponService($this->wc, $codeGen);

        $this->service->create([
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 50,
            'email'         => 'test@test.com',
            'categories'    => [31, 67],
        ]);

        $this->wc->shouldHaveReceived('getProductsByCategory')->twice();
        $this->assertTrue(true); // Mockery assertion arriba confirma el comportamiento
    }

    public function test_night_sale_expiration_is_always_24_hours(): void
    {
        $coupon = $this->service->create([
            'type'            => 'night_sale',
            'discount_type'   => 'percent',
            'amount'          => 40,
            'expiration_days' => 365,
        ]);

        // Carbon 3: diffInHours() puede devolver valor con signo; usamos abs() para portabilidad
        $diff = abs($coupon->expires_at->diffInHours(now()));

        $this->assertTrue($diff >= 23 && $diff <= 25);
    }

    public function test_deleted_coupon_fails_validation(): void
    {
        $coupon = $this->service->create([
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 50,
            'email'         => 'test@test.com',
        ]);

        $coupon->delete();
        $coupon->status = 'deleted';
        $coupon->save();

        $result = $this->service->validate($coupon, 'test@test.com', []);

        $this->assertFalse($result['valid']);
    }

    public function test_bulk_continues_after_partial_failure(): void
    {
        $this->wc = Mockery::mock(WooCommerceClientInterface::class);
        $this->wc->shouldReceive('findCouponByCode')->andReturn(null);
        $this->wc->shouldReceive('createCoupon')
            ->times(10)
            ->andReturnUsing(function () {
                static $callCount = 0;
                $callCount++;
                if ($callCount === 5) {
                    throw new \Exception('WooCommerce error');
                }
                return ['id' => 999 + $callCount];
            });
        $this->wc->shouldReceive('trashCoupon')->andReturn(['id' => 999, 'status' => 'trash']);

        $codeGen = new CodeGenerator($this->wc);
        $this->service = new CouponService($this->wc, $codeGen);

        $result = $this->service->createBulk([
            'quantity'      => 10,
            'type'          => 'birthday',
            'discount_type' => 'percent',
            'amount'        => 50,
            'email'         => 'bulk@test.com',
        ]);

        $this->assertTrue($result['created'] > 0);
        $this->assertTrue($result['failed'] > 0);
        $this->assertEquals(10, $result['created'] + $result['failed']);
    }
}
