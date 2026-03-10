<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class ValidateCouponRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'email'        => 'required|email',
            'product_ids'  => 'array',
            'product_ids.*' => 'integer',
            'cart_total'   => 'numeric|nullable',
        ];
    }
}
