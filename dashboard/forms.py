# forms.py
from django import forms
from bakery.models import ProductCategory, ProductSubCategory, ProductBatch

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['category_name', 'description']


class ProductSubCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductSubCategory
        fields = ['product_category', 'sub_category_name']

class ProductBatchForm(forms.ModelForm):
    class Meta:
        model = ProductBatch
        fields = ['product', 'batch_number', 'quantity', 'expiry_date']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'})
        }