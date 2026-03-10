<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class ApiKeyMiddleware
{
    public function handle(Request $request, Closure $next): mixed
    {
        $key = $request->header('X-API-Key');
        if ($key !== config('app.api_key')) {
            return response()->json([
                'data'  => null,
                'meta'  => ['timestamp' => now()->toIso8601String()],
                'error' => 'Unauthorized',
            ], 401);
        }
        return $next($request);
    }
}
