from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from . import catalog_csv
from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("article", "name", "manufacturer", "collection", "price", "price_unit", "on_sale")
    search_fields = ("article", "name", "manufacturer", "collection")
    list_filter = ("kind", "manufacturer", "on_sale", "is_accessory")
    change_list_template = "admin/shop/product/change_list.html"
    prepopulated_fields = {"article": ("name",)}

    def get_urls(self):
        return [
            path("import/", self.admin_site.admin_view(self.import_csv), name="shop_product_import"),
            path("export/", self.admin_site.admin_view(self.export_csv), name="shop_product_export"),
        ] + super().get_urls()

    def import_csv(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = catalog_csv.UploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                count = catalog_csv.import_products(form.cleaned_data["csv_file"],
                                                    can_change=self.has_change_permission(request))
            except ValidationError as error:
                form.add_error("csv_file", error)
            else:
                self.message_user(request, f"Импортировано товаров: {count}", level=messages.SUCCESS)
                return redirect("admin:shop_product_changelist")
        return TemplateResponse(request, "admin/shop/product/import_csv.html", {
            **self.admin_site.each_context(request), "title": "Импорт товаров из CSV",
            "form": form, "opts": self.model._meta,
        })

    def export_csv(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="plitka24-products.csv"'
        catalog_csv.export_products(response, self.get_queryset(request))
        return response


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ("article", "product_name", "unit_price", "quantity", "unit", "line_total")
    readonly_fields = fields
    extra = 0
    can_delete = False

    @admin.display(description="Сумма")
    def line_total(self, item):
        return item.total

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "status", "order_total")
    list_filter = ("status",)
    list_select_related = ("user",)
    search_fields = ("user__username",)
    readonly_fields = ("user", "comments", "created_at", "order_total")
    inlines = (OrderItemInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items")

    @admin.display(description="Сумма")
    def order_total(self, order):
        return order.total

    def has_add_permission(self, request):
        return False
