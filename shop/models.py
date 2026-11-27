from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse


class Product(models.Model):
    """A tile or accessory. Cart prices are calculated per pack when specified."""

    class PriceUnit(models.TextChoices):
        PACKAGE = "package", "упак."
        SQUARE_METRE = "m2", "м²"
        PIECE = "piece", "шт."

    class Swatch(models.TextChoices):
        SAND = "sand", "Песчаник"
        CHALK = "chalk", "Мел"
        SAGE = "sage", "Шалфей"
        CLAY = "clay", "Терракота"
        INK = "ink", "Графит"
        TERRAZZO = "terrazzo", "Терраццо"
        MOSAIC = "mosaic", "Мозаика"
        GROUT = "grout", "Затирка"

    article = models.SlugField("Артикул", max_length=40, unique=True)
    name = models.CharField("Наименование", max_length=150)
    manufacturer = models.CharField("Бренд", max_length=80)
    collection = models.CharField("Коллекция", max_length=80, blank=True)
    kind = models.CharField("Назначение", max_length=60)
    material = models.CharField("Материал", max_length=60, blank=True)
    surface = models.CharField("Поверхность", max_length=60, blank=True)
    color = models.CharField("Цвет", max_length=60, blank=True)
    size = models.CharField("Размер, см", max_length=40, blank=True)
    pack_units = models.PositiveSmallIntegerField("Штук в упаковке", null=True, blank=True,
                                                  validators=[MinValueValidator(1)])
    pack_m2 = models.DecimalField("м² в упаковке", max_digits=6, decimal_places=3, null=True,
                                  blank=True, validators=[MinValueValidator(Decimal("0.001"))])
    price = models.DecimalField("Цена", max_digits=9, decimal_places=2,
                                validators=[MinValueValidator(Decimal("0.00"))])
    price_unit = models.CharField("Единица цены", max_length=10, choices=PriceUnit,
                                  default=PriceUnit.PACKAGE)
    swatch = models.CharField("Иллюстрация", max_length=15, choices=Swatch, default=Swatch.SAND)
    is_accessory = models.BooleanField("Аксессуар", default=False)
    on_sale = models.BooleanField("Распродажа", default=False)

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["article"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shop:product_detail", args=[self.article])

    @property
    def image_url(self):
        swatch = self.swatch if self.swatch in self.Swatch.values else self.Swatch.SAND
        return static(f"images/{swatch}.svg")

    @property
    def cart_price(self):
        multiplier = 1
        if self.price_unit == self.PriceUnit.SQUARE_METRE and self.pack_m2:
            multiplier = self.pack_m2
        elif self.price_unit == self.PriceUnit.PIECE and self.pack_units:
            multiplier = self.pack_units
        return (self.price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def cart_unit(self):
        if ((self.price_unit == self.PriceUnit.SQUARE_METRE and self.pack_m2)
                or (self.price_unit == self.PriceUnit.PIECE and self.pack_units)):
            return self.PriceUnit.PACKAGE.label
        return self.get_price_unit_display()


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        PROCESSING = "processing", "В обработке"
        READY = "ready", "Готов к выдаче"
        COMPLETED = "completed", "Выдан"
        CANCELLED = "cancelled", "Отменён"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="orders", verbose_name="Пользователь")
    status = models.CharField("Статус", max_length=20, choices=Status, default=Status.NEW)
    comments = models.CharField("Комментарий", max_length=500, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"Заказ №{self.pk}"

    @property
    def total(self):
        return sum((item.total for item in self.items.all()), Decimal("0.00"))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    article = models.CharField("Артикул", max_length=40)
    product_name = models.CharField("Товар", max_length=150)
    unit_price = models.DecimalField("Цена за единицу", max_digits=16, decimal_places=2)
    quantity = models.PositiveSmallIntegerField("Количество")
    unit = models.CharField("Единица", max_length=8)

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"
        ordering = ["pk"]
        constraints = [models.CheckConstraint(
            condition=models.Q(quantity__gte=1, quantity__lte=99, unit_price__gte=0),
            name="valid_order_item",
        )]

    def __str__(self):
        return self.product_name

    @property
    def total(self):
        return self.unit_price * self.quantity
