"""
Forms for the Dashboard app.

Django `Form` is the server-rendered equivalent of a DRF serializer:
input validation lives here, never in a view. Uniqueness/format checks
reuse the exact same helpers as the API layer (`CustomerSelector`,
`is_valid_phone_number`) so the two transports can never disagree about
what's a valid customer.
"""

from typing import Any
from uuid import UUID

from django import forms

from apps.customers.constants import CustomerGender, CustomerStatus
from apps.customers.selectors import CustomerSelector
from apps.customers.validators import is_valid_phone_number


class LoginForm(forms.Form):
    """Validates email/password input on the login page."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class CustomerForm(forms.Form):
    """Validates create/update input for a customer.

    Mirrors `CreateCustomerSerializer`/`UpdateCustomerSerializer` field for
    field. Pass `customer_id` when editing so uniqueness checks exclude the
    record being edited.
    """

    customer_code = forms.CharField(label="Mã khách hàng", max_length=20)
    full_name = forms.CharField(label="Họ và tên", max_length=150)
    phone = forms.CharField(label="Số điện thoại", max_length=20)
    email = forms.EmailField(label="Email", max_length=255, required=False)
    gender = forms.ChoiceField(
        label="Giới tính",
        choices=[("", "—"), *CustomerGender.choices],
        required=False,
    )
    birthday = forms.DateField(
        label="Ngày sinh",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    address = forms.CharField(
        label="Địa chỉ", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    note = forms.CharField(
        label="Ghi chú", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    status = forms.ChoiceField(label="Trạng thái", choices=CustomerStatus.choices)

    def __init__(
        self, *args: Any, customer_id: UUID | str | None = None, **kwargs: Any
    ) -> None:
        """Store the customer being edited (if any) for uniqueness checks."""
        self.customer_id = customer_id
        super().__init__(*args, **kwargs)

    def clean_customer_code(self) -> str:
        """Validate that the customer code is unique (excluding self).

        Returns:
            The validated customer code.

        Raises:
            forms.ValidationError: If another customer uses this code.
        """
        value = self.cleaned_data["customer_code"]
        if CustomerSelector.code_exists(value, exclude_id=self.customer_id):
            raise forms.ValidationError(f"Mã khách hàng '{value}' đã tồn tại.")
        return value

    def clean_phone(self) -> str:
        """Validate phone format and uniqueness (excluding self).

        Returns:
            The validated phone number.

        Raises:
            forms.ValidationError: If the format is invalid or another
                customer already uses this phone number.
        """
        value = self.cleaned_data["phone"]
        if not is_valid_phone_number(value):
            raise forms.ValidationError(
                "Số điện thoại phải có 9-15 chữ số, có thể bắt đầu bằng '+'."
            )
        if CustomerSelector.phone_exists(value, exclude_id=self.customer_id):
            raise forms.ValidationError(f"Số điện thoại '{value}' đã được sử dụng.")
        return value
