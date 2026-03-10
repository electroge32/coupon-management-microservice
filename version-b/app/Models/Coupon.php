<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Coupon extends Model
{
    use SoftDeletes;

    protected $fillable = [
        'wc_id',
        'code',
        'type',
        'discount_type',
        'amount',
        'allowed_email',
        'use_count',
        'usage_limit',
        'expires_at',
        'status',
        'categories',
        'meta',
    ];

    protected $casts = [
        'categories' => 'array',
        'meta'       => 'array',
        'expires_at' => 'datetime',
        'amount'     => 'decimal:2',
    ];

    public function usages(): HasMany
    {
        return $this->hasMany(CouponUsage::class);
    }

    public function isExpired(): bool
    {
        if (!$this->expires_at) return false;
        return $this->expires_at->isPast();
    }

    public function hasReachedLimit(): bool
    {
        if ($this->usage_limit === null) return false;
        return $this->use_count >= $this->usage_limit;
    }
}
