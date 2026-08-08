from django import forms

from product.models import Category, Product


class ProductUIForm(forms.ModelForm):
    # Khai báo riêng 2 trường này là CharField để nhận dấu phẩy không bị lỗi Django Validation
    cost_price = forms.CharField(
        label="Giá nhập",
        widget=forms.TextInput(attrs={"class": "form-control currency-input", "placeholder": "1,000"}),
        required=True
    )
    selling_price = forms.CharField(
        label="Giá bán",
        widget=forms.TextInput(attrs={"class": "form-control currency-input", "placeholder": "1,000"}),
        required=True
    )

    class Meta:
        model = Product
        fields = [
            "sku", "name", "category", "description",
            "image", "cost_price", "selling_price", "unit", "status"
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ví dụ: SP001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên sản phẩm..."}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Mô tả..."}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "unit": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Định dạng có dấu phẩy khi tải dữ liệu cũ (Trang Sửa sản phẩm)
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

    # Xử lý làm sạch và kiểm tra Giá nhập
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

    # Xử lý làm sạch và kiểm tra Giá bán
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


# class CategoryForm(forms.ModelForm):
#     class Meta:
#         model = Category
#         fields = ["name", "description"]
#         widgets = {
#             "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên danh mục"}),
#             "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Mô tả danh mục..."}),
#         }
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tên danh mục"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Mô tả danh mục..."}),
        }
