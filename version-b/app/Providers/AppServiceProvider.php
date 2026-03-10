<?php

namespace App\Providers;

use App\Contracts\WooCommerceClientInterface;
use App\Services\WooCommerceClient;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(WooCommerceClientInterface::class, WooCommerceClient::class);
    }

    public function boot(): void
    {
        //
    }
}
