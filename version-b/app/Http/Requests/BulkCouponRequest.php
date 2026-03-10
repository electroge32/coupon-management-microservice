<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class BulkCouponRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'type'            => 'required|in:birthday,gift_card,referral,partner,night_sale,campaign',
            'discount_type'   => 'required|in:percent,fixed_cart,fixed_product',
            'amount'          => 'required|numeric|min:0',
            'categories'      => 'array',
            'categories.*'    => 'integer',
            'usage_limit'     => 'integer|min:1|nullable',
            'expiration_days' => 'integer|min:1|nullable',
            'expires_at'      => 'date|nullable',
            'prefix'          => 'string|nullable',
            'quantity'        => 'required|integer|min:1|max:500',
        ];
    }
}
