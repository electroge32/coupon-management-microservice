<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class UpdateCouponRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'amount'      => 'numeric|min:0|nullable',
            'email'       => 'email|nullable',
            'usage_limit' => 'integer|min:1|nullable',
            'expires_at'  => 'date|nullable',
            'status'      => 'string|in:active,inactive,deleted|nullable',
        ];
    }
}
