from django import forms
from django.contrib.auth import get_user_model

from .cart import MAX_QUANTITY
from .models import Order


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=MAX_QUANTITY)


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("comments",)
        widgets = {"comments": forms.Textarea(attrs={"rows": 3, "placeholder": "Необязательное поле"})}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name")
