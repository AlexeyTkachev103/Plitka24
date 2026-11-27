from dataclasses import dataclass
from decimal import Decimal

from .models import Product

MAX_QUANTITY = 99
MAX_PRODUCTS = 50


@dataclass(frozen=True)
class Line:
    product: Product
    quantity: int

    @property
    def total(self):
        return self.product.cart_price * self.quantity


def lines(request):
    cart = request.session.get("cart", {})
    products = Product.objects.filter(pk__in=cart)
    result = [Line(product, cart[str(product.pk)]) for product in products]
    if len(result) != len(cart):
        request.session["cart"] = {str(line.product.pk): line.quantity for line in result}
    return result


def total(cart_lines):
    return sum((line.total for line in cart_lines), Decimal("0.00"))


def context(request):
    return {"cart_count": sum(request.session.get("cart", {}).values())}
