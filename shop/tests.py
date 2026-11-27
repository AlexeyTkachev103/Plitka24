import csv
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .catalog_csv import FIELDS
from .models import Order, Product

User = get_user_model()


def url(name, *args):
    return reverse(f"shop:{name}", args=args)


class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_seed_can_run_again_without_overwriting_edits(self):
        Product.objects.filter(article="D101").update(name="Переименовано")
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Product.objects.count(), 16)
        self.assertEqual(Product.objects.get(article="D101").name, "Переименовано")

    def test_catalog_search_and_filter(self):
        response = self.client.get(url("product_list"), {"q": "D10", "kind": "Настенная"})
        self.assertContains(response, "Утренний мел")
        self.assertNotContains(response, "Тёплый песок")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(self.client.get(url("product_list"), {"q": "шалфей"}), "Форма Шалфей")
        self.assertContains(self.client.get(url("product_list"), {"q": "["}), "Товары не найдены")

    def test_sections_and_pagination(self):
        response = self.client.get(url("product_list"))
        self.assertEqual(response.context["page_obj"].paginator.count, 14)
        self.assertContains(self.client.get(url("product_list"), {"page": 2}), "Тон Красная охра")
        self.assertEqual(self.client.get(url("accessories_page")).context["page_obj"].paginator.count, 2)
        self.assertEqual(self.client.get(url("sale_page")).context["page_obj"].paginator.count, 4)
        self.assertContains(self.client.get(url("collections_page")), "Дюны")
        self.assertContains(self.client.get(url("tile_page")), "Рассчитайте площадь")

    def test_product_renders_with_package_price_and_missing_product_returns_404(self):
        response = self.client.get(url("product_detail", "D101"))
        self.assertContains(response, "Травертин Тёплый песок")
        self.assertContains(response, "/static/images/sand.svg")
        self.assertContains(response, "2\xa0721,60")
        self.assertEqual(self.client.get(url("product_detail", "missing")).status_code, 404)


class ShoppingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(article="T001", name="Demo tile", manufacturer="Demo",
                                             kind="Floor", price=Decimal("10.25"), pack_m2=Decimal("1.42"),
                                             price_unit="m2")
        cls.shopper = User.objects.create_user(username="shopper")

    def setUp(self):
        self.update = url("cart_update", self.product.pk)

    def test_cart_add_update_remove(self):
        self.assertEqual(self.client.post(self.update, {"action": "add"}, HTTP_ACCEPT="application/json").json(),
                         {"count": 1})
        self.assertRedirects(self.client.post(self.update, {"quantity": 2}), url("cart_detail"))
        response = self.client.get(url("cart_detail"))
        self.assertContains(response, "Demo tile")
        self.assertEqual(response.context["total"], Decimal("29.12"))
        self.client.post(self.update, {"quantity": 0})
        self.assertContains(self.client.get(url("cart_detail")), "Корзина пуста")

    def test_cart_drops_catalog_items_that_were_deleted(self):
        self.client.post(self.update, {"quantity": 2})
        self.product.delete()
        self.assertContains(self.client.get(url("cart_detail")), "Корзина пуста")
        self.assertEqual(self.client.session["cart"], {})

    def test_cart_quantity_validation(self):
        response = self.client.post(self.update, {"quantity": 100}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("cart", self.client.session)

    def test_cart_post_requires_csrf_and_get_cannot_modify_it(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(self.update).status_code, 405)
        self.assertEqual(client.post(self.update, {"action": "add"}).status_code, 403)

    def test_checkout_and_history_keep_snapshot_and_require_owner(self):
        self.client.post(self.update, {"quantity": 2})
        self.assertRedirects(self.client.get(url("checkout")), url("login") + "?next=/checkout/")
        self.client.force_login(self.shopper)
        self.assertContains(self.client.get(url("checkout")), "Оформление демо-заказа")
        response = self.client.post(url("checkout"), {"comments": "Demo only"})
        order = Order.objects.get(user=self.shopper)
        self.assertRedirects(response, url("order_detail", order.pk))
        self.assertEqual(order.total, Decimal("29.12"))
        self.assertNotIn("cart", self.client.session)
        self.product.delete()
        self.assertContains(self.client.get(url("order_detail", order.pk)), "Demo tile")
        self.assertContains(self.client.get(url("profile")), f"№{order.pk}")
        self.client.force_login(User.objects.create_user(username="other-shopper"))
        self.assertEqual(self.client.get(url("order_detail", order.pk)).status_code, 404)
        self.assertNotContains(self.client.get(url("profile")), f"№{order.pk}")

    def test_empty_checkout_cannot_create_an_order(self):
        self.client.force_login(self.shopper)
        self.assertRedirects(self.client.post(url("checkout")), url("cart_detail"))
        self.assertFalse(Order.objects.exists())

    def test_registration_login_and_logout(self):
        password = "Synthetic-demo-credential-4023"
        response = self.client.post(url("register"), {
            "username": "demo-visitor", "password1": password, "password2": password,
        })
        self.assertRedirects(response, url("profile"))
        self.assertEqual(User.objects.get(username="demo-visitor").email, "")
        self.assertEqual(self.client.get(url("logout")).status_code, 405)
        self.assertRedirects(self.client.post(url("logout")), url("product_list"))
        self.assertRedirects(self.client.post(url("login"), {"username": "demo-visitor", "password": password}),
                             url("profile"))


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(username="site-admin")
        cls.staff = User.objects.create_user(username="staff-with-no-model-permissions", is_staff=True)
        cls.order = Order.objects.create(user=User.objects.create_user(username="buyer"))

    @staticmethod
    def upload(content):
        return {"csv_file": SimpleUploadedFile("demo.csv", content, content_type="text/csv")}

    def test_csv_requires_product_permissions(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("admin:shop_product_export")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:shop_product_import")).status_code, 403)

    def test_csv_examples_import_and_export(self):
        self.client.force_login(self.admin)
        import_url = reverse("admin:shop_product_import")
        self.assertContains(self.client.get(import_url), "Импорт товаров из CSV")
        content = (settings.BASE_DIR / "examples/products.csv").read_bytes()
        self.assertRedirects(self.client.post(import_url, self.upload(content)),
                             reverse("admin:shop_product_changelist"))
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Product.objects.get(article="EX001").price, Decimal("1950.00"))
        self.assertTrue(Product.objects.get(article="EX002").is_accessory)
        response = self.client.get(reverse("admin:shop_product_export"))
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual([row["article"] for row in rows], ["EX001", "EX002"])
        self.assertRedirects(self.client.post(import_url, self.upload(response.content)),
                             reverse("admin:shop_product_changelist"))
        self.assertEqual(Product.objects.count(), 2)

    def test_bad_csv_row_does_not_write_partial_import(self):
        self.client.force_login(self.admin)
        source = (settings.BASE_DIR / "examples/products.csv").read_text(encoding="utf-8")
        response = self.client.post(reverse("admin:shop_product_import"),
                                    self.upload(source.replace("520.00", "-520.00").encode("utf-8")))
        self.assertContains(response, "Строка 3")
        self.assertFalse(Product.objects.exists())

    def test_csv_export_treats_formula_markers_as_text(self):
        self.client.force_login(self.admin)
        Product.objects.create(article="T001", name="=1+1", manufacturer="Demo", kind="Floor", price=1)
        response = self.client.get(reverse("admin:shop_product_export"))
        reader = csv.DictReader(StringIO(response.content.decode()))
        self.assertEqual(reader.fieldnames, list(FIELDS))
        self.assertEqual(next(reader)["name"], "'=1+1")

    def test_admin_status_update(self):
        self.client.force_login(self.admin)
        change = reverse("admin:shop_order_change", args=[self.order.pk])
        self.assertEqual(self.client.get(change).status_code, 200)
        self.assertRedirects(self.client.post(change, {"status": "ready", "items-TOTAL_FORMS": "0",
                                                        "items-INITIAL_FORMS": "0"}),
                             reverse("admin:shop_order_changelist"))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY)
