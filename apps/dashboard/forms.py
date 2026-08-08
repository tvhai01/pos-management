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
#import Product, Category models for product forms
from apps.product.models import Category, Product




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

#products

class ProductUIForm(forms.ModelForm):
    cost_price = forms.CharField(
        label="Giá nhập",
        widget=forms.TextInput(attrs={"class": "form-control currency-input", "placeholder": "1,000"}),
        required=True,
    )
    selling_price = forms.CharField(
        label="Giá bán",
        widget=forms.TextInput(attrs={"class": "form-control currency-input", "placeholder": "1,000"}),
        required=True,
    )

    class Meta:
        model = Product
        fields = [
            "sku", "name", "category", "unit", "image", "cost_price", "selling_price", "status"
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ví dụ: SP001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên sản phẩm..."}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            if self.instance.cost_price is not None:
                self.initial['cost_price'] = f"{int(self.instance.cost_price):,}"
            if self.instance.selling_price is not None:
                self.initial['selling_price'] = f"{int(self.instance.selling_price):,}"

        is_editing = self.instance and not self.instance._state.adding

        if is_editing:
            self.fields['sku'].disabled = True
            # PRODUCT_TXN_GUARD — khóa SKU khi đã có giao dịch (xem Product.has_transaction_history)
            if self.instance.has_transaction_history():
                self.fields['sku'].help_text = "Mã SKU bị khóa do sản phẩm đã phát sinh giao dịch."
            else:
                self.fields['sku'].help_text = "Mã SKU không thể thay đổi khi cập nhật."
        else:
            self.fields['sku'].disabled = False
            self.fields['sku'].required = True

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        is_editing = self.instance and not self.instance._state.adding

        if is_editing and self.fields['sku'].disabled:
            return self.instance.sku

        if not sku:
            raise forms.ValidationError("Vui lòng nhập mã SKU.")

        query = Product.objects.filter(sku=sku)
        if is_editing:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise forms.ValidationError("Mã SKU này đã tồn tại trong hệ thống.")

        return sku

    def clean_cost_price(self):
        val_str = str(self.cleaned_data.get('cost_price', '')).replace(',', '').strip()
        if not val_str:
            raise forms.ValidationError("Vui lòng nhập giá nhập.")
        try:
            val = float(val_str)
            if val < 1:
                raise forms.ValidationError("Giá nhập phải lớn hơn hoặc bằng 1.")
            return val
        except ValueError:
            raise forms.ValidationError("Giá nhập không hợp lệ.")

    def clean_selling_price(self):
        val_str = str(self.cleaned_data.get('selling_price', '')).replace(',', '').strip()
        if not val_str:
            raise forms.ValidationError("Vui lòng nhập giá bán.")
        try:
            val = float(val_str)
            if val < 1:
                raise forms.ValidationError("Giá bán phải lớn hơn hoặc bằng 1.")
            return val
        except ValueError:
            raise forms.ValidationError("Giá bán không hợp lệ.")

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')

        if cost_price is not None and selling_price is not None:
            if selling_price <= cost_price:
                self.add_error('selling_price', "Giá bán phải lớn hơn giá nhập.")

        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên danh mục"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Mô tả danh mục..."}),
        }