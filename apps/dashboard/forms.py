"""Validation forms for the session-authenticated Dashboard UI."""

from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID

from django import forms

from apps.customers.constants import CustomerGender, CustomerStatus
from apps.customers.selectors import CustomerSelector
from apps.customers.validators import is_valid_phone_number
from apps.inventory.constants import MSG_INVALID_QUANTITY, StockMovementType
from apps.product.constants import MSG_INVALID_PRODUCT_PRICES
from apps.product.models import Category, Product
from apps.product.selectors import CategorySelector, ProductSelector
from apps.product.validators import (
    has_valid_price_relationship,
    normalize_category_name,
    normalize_sku,
    parse_price,
)


class LoginForm(forms.Form):
    """Validate email and password input on the login page."""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class CustomerForm(forms.Form):
    """Validate Customer create/update input for the HTML dashboard."""

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
        label="Địa chỉ",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    note = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    status = forms.ChoiceField(label="Trạng thái", choices=CustomerStatus.choices)

    def __init__(
        self, *args: Any, customer_id: UUID | str | None = None, **kwargs: Any
    ) -> None:
        """Store the edited customer ID for uniqueness checks."""
        self.customer_id = customer_id
        super().__init__(*args, **kwargs)

    def clean_customer_code(self) -> str:
        """Validate customer-code uniqueness while excluding the current row."""
        value = self.cleaned_data["customer_code"]
        if CustomerSelector.code_exists(value, exclude_id=self.customer_id):
            raise forms.ValidationError(f"Mã khách hàng '{value}' đã tồn tại.")
        return value

    def clean_phone(self) -> str:
        """Validate phone format and uniqueness."""
        value = self.cleaned_data["phone"]
        if not is_valid_phone_number(value):
            raise forms.ValidationError(
                "Số điện thoại phải có 9-15 chữ số, có thể bắt đầu bằng '+'."
            )
        if CustomerSelector.phone_exists(value, exclude_id=self.customer_id):
            raise forms.ValidationError(f"Số điện thoại '{value}' đã được sử dụng.")
        return value


class ProductUIForm(forms.ModelForm):
    """Validate Product create/update input for the HTML dashboard."""

    cost_price = forms.CharField(
        label="Giá nhập",
        widget=forms.TextInput(
            attrs={"class": "currency-input", "placeholder": "1,000"}
        ),
    )
    selling_price = forms.CharField(
        label="Giá bán",
        widget=forms.TextInput(
            attrs={"class": "currency-input", "placeholder": "1,200"}
        ),
    )

    class Meta:
        model = Product
        fields: ClassVar[tuple[str, ...]] = (
            "sku",
            "name",
            "description",
            "category",
            "unit",
            "image",
            "cost_price",
            "selling_price",
            "status",
        )
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure Category choices and immutable SKU behavior."""
        super().__init__(*args, **kwargs)
        category_field = self.fields["category"]
        if isinstance(category_field, forms.ModelChoiceField):
            category_field.queryset = CategorySelector.get_all_categories()

        is_editing = bool(self.instance and not self.instance._state.adding)
        if is_editing:
            self.fields["sku"].disabled = True
            self.fields["sku"].help_text = "Mã SKU không thể thay đổi sau khi tạo."
            self.initial["cost_price"] = f"{self.instance.cost_price:,.0f}"
            self.initial["selling_price"] = f"{self.instance.selling_price:,.0f}"

    def clean_sku(self) -> str:
        """Normalize and validate SKU uniqueness across all rows."""
        if self.instance and not self.instance._state.adding:
            return self.instance.sku
        sku = normalize_sku(self.cleaned_data["sku"])
        if ProductSelector.sku_exists(sku):
            raise forms.ValidationError("Mã SKU này đã tồn tại trong hệ thống.")
        return sku

    def clean_cost_price(self) -> Decimal:
        """Parse a positive cost price without floating-point conversion."""
        price = parse_price(self.cleaned_data.get("cost_price", ""))
        if price is None:
            raise forms.ValidationError("Giá nhập phải là một số lớn hơn 0.")
        return price

    def clean_selling_price(self) -> Decimal:
        """Parse a positive selling price without floating-point conversion."""
        price = parse_price(self.cleaned_data.get("selling_price", ""))
        if price is None:
            raise forms.ValidationError("Giá bán phải là một số lớn hơn 0.")
        return price

    def clean(self) -> dict[str, Any]:
        """Validate the relationship between cost and selling price."""
        cleaned_data = super().clean() or {}
        cost_price = cleaned_data.get("cost_price")
        selling_price = cleaned_data.get("selling_price")
        if (
            cost_price is not None
            and selling_price is not None
            and not has_valid_price_relationship(cost_price, selling_price)
        ):
            self.add_error("selling_price", MSG_INVALID_PRODUCT_PRICES)
        return cleaned_data


class CategoryForm(forms.ModelForm):
    """Validate Category create/update input for the HTML dashboard."""

    class Meta:
        model = Category
        fields: ClassVar[tuple[str, ...]] = ("name", "description")
        widgets: ClassVar[dict[str, forms.Widget]] = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self) -> str:
        """Normalize and validate category-name uniqueness."""
        name = normalize_category_name(self.cleaned_data["name"])
        exclude_id = self.instance.id if self.instance and self.instance.pk else None
        if CategorySelector.name_exists(name, exclude_id=exclude_id):
            raise forms.ValidationError("Tên danh mục này đã tồn tại.")
        return name


class StockMovementForm(forms.Form):
    """Validate a stock mutation submitted from the Dashboard."""

    movement_type = forms.ChoiceField(
        label="Loại giao dịch",
        choices=StockMovementType.choices,
    )
    quantity = forms.DecimalField(
        label="Số lượng",
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Điều chỉnh: nhập số tồn mục tiêu. Nhập/xuất: nhập lượng thay đổi.",
    )
    reference_code = forms.CharField(
        label="Mã tham chiếu",
        max_length=100,
        required=False,
    )
    note = forms.CharField(
        label="Ghi chú",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self) -> dict[str, Any]:
        """Require positive inbound/outbound quantities."""
        cleaned_data = super().clean() or {}
        movement_type = cleaned_data.get("movement_type")
        quantity = cleaned_data.get("quantity")
        if (
            quantity is not None
            and movement_type != StockMovementType.ADJUSTMENT
            and quantity <= 0
        ):
            self.add_error("quantity", MSG_INVALID_QUANTITY)
        return cleaned_data


class LowStockThresholdForm(forms.Form):
    """Validate a non-negative Product warning threshold."""

    low_stock_threshold = forms.DecimalField(
        label="Ngưỡng tồn thấp",
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
    )
