from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "shop"
urlpatterns = [
    path("", views.catalog, name="product_list"),
    path("tile/", views.tile, name="tile_page"),
    path("collections/", views.collections, name="collections_page"),
    path("accessories/", views.catalog, {"section": "accessories"}, name="accessories_page"),
    path("sale/", views.catalog, {"section": "sale"}, name="sale_page"),
    path("product/<slug:article>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="shop/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/password/", views.password_change, name="password_change"),
]
