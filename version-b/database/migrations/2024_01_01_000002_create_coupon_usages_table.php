<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('coupon_usages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('coupon_id')->constrained('coupons');
            $table->string('email')->nullable();
            $table->string('order_id')->nullable();
            $table->timestamp('used_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('coupon_usages');
    }
};
