<?php

return [
    'name'               => env('APP_NAME', 'ADIPA Coupon Service'),
    'env'                => env('APP_ENV', 'production'),
    'debug'              => (bool) env('APP_DEBUG', false),
    'url'                => env('APP_URL', 'http://localhost'),
    'key'                => env('APP_KEY'),
    'cipher'             => 'AES-256-CBC',
    'api_key'            => env('API_KEY'),
    'max_fixed_discount' => (int) env('MAX_FIXED_DISCOUNT', 500000),
    'timezone'           => 'UTC',
    'locale'             => 'en',
    'faker_locale'       => 'es_CO',
];
