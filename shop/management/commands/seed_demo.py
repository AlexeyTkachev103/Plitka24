from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Product

# All manufacturers, collections, and products below are invented for this demo.
TILES = (
    ("D101", "Травертин Тёплый песок", "Артель Север", "Дюны", "Напольная", "Песочный", "sand", "1890", False),
    ("D102", "Травертин Утренний мел", "Артель Север", "Дюны", "Настенная", "Молочный", "chalk", "1690", False),
    ("D103", "Травертин Светлый берег", "Артель Север", "Дюны", "Напольная", "Песочный", "sand", "1590", True),
    ("F201", "Форма Шалфей", "Студия Линия", "Форма", "Настенная", "Зелёный", "sage", "2290", False),
    ("F202", "Форма Обожжённая глина", "Студия Линия", "Форма", "Настенная", "Терракотовый", "clay", "2390", False),
    ("F203", "Форма Белый рельеф", "Студия Линия", "Форма", "Настенная", "Молочный", "chalk", "1890", True),
    ("G301", "Грань Тёмный графит", "Артель Север", "Грань", "Напольная", "Графитовый", "ink", "2590", False),
    ("G302", "Грань Светлый терраццо", "Артель Север", "Грань", "Напольная", "Молочный", "terrazzo", "2490", False),
    ("G303", "Грань Каменная крошка", "Артель Север", "Грань", "Напольная", "Песочный", "terrazzo", "2090", True),
    ("M401", "Модуль Сине-зелёный", "Студия Линия", "Модуль", "Мозаика", "Зелёный", "mosaic", "890", False),
    ("M402", "Модуль Дымчатый", "Студия Линия", "Модуль", "Мозаика", "Графитовый", "ink", "790", False),
    ("M403", "Модуль Кремовый", "Студия Линия", "Модуль", "Мозаика", "Молочный", "chalk", "690", True),
    ("T501", "Тон Песочный", "Керамическое бюро 17", "Тон", "Напольная", "Песочный", "sand", "1790", False),
    ("T502", "Тон Красная охра", "Керамическое бюро 17", "Тон", "Настенная", "Терракотовый", "clay", "1990", False),
)


class Command(BaseCommand):
    help = "Populate the local demo with fictional catalog entries; existing rows are left unchanged."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for article, name, brand, collection, kind, color, swatch, price, sale in TILES:
            mosaic = kind == "Мозаика"
            _, added = Product.objects.get_or_create(article=article, defaults={
                "name": name, "manufacturer": brand, "collection": collection, "kind": kind,
                "material": "Керамика" if kind != "Напольная" else "Керамогранит",
                "surface": "Глянцевая" if mosaic else "Матовая", "color": color,
                "size": "30 × 30" if mosaic else "60 × 60", "swatch": swatch,
                "pack_m2": None if mosaic else Decimal("1.440"), "pack_units": None if mosaic else 4,
                "price": Decimal(price), "price_unit": Product.PriceUnit.PIECE if mosaic else Product.PriceUnit.SQUARE_METRE,
                "on_sale": sale,
            })
            created += added
        for article, color, price in (("A701", "Молочный", "490"), ("A702", "Графитовый", "550")):
            _, added = Product.objects.get_or_create(article=article, defaults={
                "name": f"Затирка Шов · {color.lower()}", "manufacturer": "Мастерская Шов",
                "kind": "Затирка", "material": "Цемент", "color": color, "price": Decimal(price),
                "price_unit": Product.PriceUnit.PIECE, "swatch": Product.Swatch.GROUT, "is_accessory": True,
            })
            created += added
        self.stdout.write(self.style.SUCCESS(f"Demo catalog: {created} new products."))
