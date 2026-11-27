from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.http import require_safe


@require_safe
def health(request):
    return HttpResponse("ok\n", content_type="text/plain")


admin.site.site_header = "Плитка24 · Управление демо"
admin.site.site_title = "Плитка24"
admin.site.index_title = "Каталог и заказы"
urlpatterns = [path("healthz/", health), path("admin/", admin.site.urls), path("", include("shop.urls"))]
