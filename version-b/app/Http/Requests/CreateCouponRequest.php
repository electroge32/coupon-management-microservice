<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class CreateCouponRequest extends FormRequest
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
            'email'           => 'required_if:type,birthday,gift_card,referral|email|nullable',
            'categories'      => 'array',
            'categories.*'    => 'integer',
            'products'        => 'array',
            'products.*'      => 'integer',
            'usage_limit'     => 'integer|min:1|nullable',
            'expiration_days' => 'integer|min:1|nullable',
            'expires_at'      => 'date|nullable',
            'prefix'          => 'required_if:type,campaign|string|nullable',
            'partner_code'    => 'required_if:type,partner|string|nullable',
        ];
    }
}
