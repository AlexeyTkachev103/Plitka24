import re

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Min, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
    require_safe,
)

from . import cart
from .forms import CartQuantityForm, CheckoutForm, ProfileForm
from .models import Order, OrderItem, Product

FILTERS = (
    ("kind", "kind", "Назначение"), ("brand", "manufacturer", "Бренд"),
    ("collection", "collection", "Коллекция"), ("material", "material", "Материал"),
    ("surface", "surface", "Поверхность"), ("color", "color", "Цвет"), ("size", "size", "Размер"),
)
SORTS = (
    ("", "article", "По артикулу"), ("name", "name", "По названию"),
    ("price_asc", "price", "Цена по возрастанию"), ("price_desc", "-price", "Цена по убыванию"),
)


@require_safe
def catalog(request, section="catalog"):
    base = Product.objects.all()
    if section == "accessories":
        base = base.filter(is_accessory=True)
    elif section == "sale":
        base = base.filter(on_sale=True)
    else:
        base = base.filter(is_accessory=False)

    products = base
    term = request.GET.get("q", "").strip()[:120]
    if term:
        # SQLite LIKE only folds ASCII. Its Django REGEXP function uses Unicode case matching.
        literal = re.escape(term)
        products = products.filter(Q(name__iregex=literal) | Q(article__iregex=literal))
    filters = []
    for name, field, label in FILTERS:
        selected = request.GET.get(name, "")
        if selected:
            products = products.filter(**{field: selected})
        options = base.exclude(**{field: ""}).order_by(field).values_list(field, flat=True).distinct()
        filters.append((name, label, list(options), selected))

    sort = request.GET.get("sort", "")
    sort_field = {key: field for key, field, _ in SORTS}.get(sort, "article")
    page = Paginator(products.order_by(sort_field, "pk"), 12).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "shop/catalog.html", {
        "section": section, "title": {"catalog": "Каталог плитки", "accessories": "Аксессуары",
                                       "sale": "Распродажа"}[section],
        "page_obj": page, "filters": filters, "sorts": SORTS, "sort": sort, "term": term,
        "querystring": query.urlencode(), "show_hero": section == "catalog" and not query,
    })


@require_safe
def tile(request):
    kinds = (Product.objects.filter(is_accessory=False).order_by("kind")
             .values_list("kind", flat=True).distinct())
    return render(request, "shop/tile.html", {"kinds": kinds})


@require_safe
def collections(request):
    groups = (Product.objects.filter(is_accessory=False).exclude(collection="")
              .values("manufacturer", "collection").annotate(count=Count("pk"), artwork=Min("swatch"))
              .order_by("collection", "manufacturer"))
    for group in groups:
        group["image"] = static(f"images/{group['artwork']}.svg")
    return render(request, "shop/collections.html", {"groups": groups})


@require_safe
def product_detail(request, article):
    return render(request, "shop/product_detail.html", {
        "product": get_object_or_404(Product, article=article),
    })


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    wants_json = request.headers.get("Accept") == "application/json"
    quantities = request.session.get("cart", {}).copy()
    key = str(product.pk)
    if request.POST.get("action") == "add":
        quantity = min(quantities.get(key, 0) + 1, cart.MAX_QUANTITY)
    else:
        form = CartQuantityForm(request.POST)
        quantity = form.cleaned_data["quantity"] if form.is_valid() else None

    error = None
    if quantity is None:
        error = f"Введите количество от 0 до {cart.MAX_QUANTITY}."
    elif not quantity:
        quantities.pop(key, None)
    elif key in quantities or len(quantities) < cart.MAX_PRODUCTS:
        quantities[key] = quantity
    else:
        error = "В корзине слишком много разных товаров."

    if error:
        if wants_json:
            return JsonResponse({"error": error}, status=400)
        messages.error(request, error)
    else:
        request.session["cart"] = quantities
        if wants_json:
            return JsonResponse({"count": sum(quantities.values())})
    return redirect("shop:cart_detail")


@require_safe
def cart_detail(request):
    lines = cart.lines(request)
    return render(request, "shop/cart.html", {"lines": lines, "total": cart.total(lines)})


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def checkout(request):
    lines = cart.lines(request)
    if not lines:
        return redirect("shop:cart_detail")
    form = CheckoutForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            OrderItem.objects.bulk_create([
                OrderItem(order=order, article=line.product.article, product_name=line.product.name,
                          unit_price=line.product.cart_price, quantity=line.quantity, unit=line.product.cart_unit)
                for line in lines
            ])
        request.session.pop("cart", None)
        messages.success(request, "Демонстрационный заказ оформлен. Оплата не требуется.")
        return redirect("shop:order_detail", order_id=order.pk)
    return render(request, "shop/checkout.html", {"form": form, "lines": lines, "total": cart.total(lines)})


@require_http_methods(["GET", "HEAD", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("shop:profile")
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("shop:profile")
    return render(request, "shop/form.html", {"form": form, "title": "Регистрация", "action": "Создать аккаунт"})


@login_required
@require_safe
def profile(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "shop/profile.html", {"orders": orders})


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def profile_edit(request):
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("shop:profile")
    return render(request, "shop/form.html", {"form": form, "title": "Профиль", "action": "Сохранить"})


@login_required
@require_http_methods(["GET", "HEAD", "POST"])
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        update_session_auth_hash(request, form.save())
        messages.success(request, "Пароль изменён.")
        return redirect("shop:profile")
    return render(request, "shop/form.html", {"form": form, "title": "Изменить пароль", "action": "Сохранить"})


@login_required
@require_safe
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=order_id, user=request.user)
    return render(request, "shop/order_detail.html", {"order": order})
