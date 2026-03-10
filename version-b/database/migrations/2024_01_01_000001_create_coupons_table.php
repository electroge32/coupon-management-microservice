<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('coupons', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('wc_id')->nullable();
            $table->string('code', 50)->unique();
            $table->string('type', 20);
            $table->string('discount_type', 20);
            $table->decimal('amount', 10, 2);
            $table->string('allowed_email', 255)->nullable();
            $table->integer('use_count')->default(0);
            $table->integer('usage_limit')->nullable();
            $table->dateTime('expires_at')->nullable();
            $table->string('status', 10)->default('active');
            $table->json('categories')->nullable();
            $table->json('meta')->nullable();
            $table->timestamps();
            $table->softDeletes();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('coupons');
    }
};
