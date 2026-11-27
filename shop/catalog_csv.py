"""Validated CSV interchange for the demo catalog. No media or URLs are imported."""
import csv
from io import StringIO

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Product

FIELDS = (
    "article", "name", "manufacturer", "collection", "kind", "material", "surface", "color", "size",
    "pack_units", "pack_m2", "price", "price_unit", "swatch", "is_accessory", "on_sale",
)
FLAGS = ("is_accessory", "on_sale")
MAX_BYTES = 256 * 1024
MAX_ROWS = 200


class ProductRowForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = FIELDS


class UploadForm(forms.Form):
    csv_file = forms.FileField(label="CSV-файл (UTF-8)", help_text="До 200 строк и 256 КиБ.")

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if upload.size > MAX_BYTES:
            raise ValidationError("Файл слишком большой.")
        return upload


def parse_flag(value):
    value = value.strip().lower()
    if value in ("1", "true"):
        return True
    if value in ("", "0", "false"):
        return False
    raise ValidationError("Для логических полей используйте 1 или 0.")


@transaction.atomic
def import_products(upload, *, can_change):
    try:
        text = upload.read(MAX_BYTES + 1).decode("utf-8-sig")
        if "\x00" in text:
            raise ValidationError("Файл должен быть текстовым CSV.")
        rows = csv.DictReader(StringIO(text, newline=""), strict=True)
        if not rows.fieldnames or len(rows.fieldnames) != len(FIELDS) or set(rows.fieldnames) != set(FIELDS):
            raise ValidationError("Заголовок не соответствует образцу CSV.")
        instances = []
        seen = set()
        for number, row in enumerate(rows, start=2):
            if number > MAX_ROWS + 1:
                raise ValidationError("Слишком много строк.")
            if None in row or None in row.values():
                raise ValidationError(f"Строка {number}: неверное число столбцов.")
            article = row["article"].strip()
            if article in seen:
                raise ValidationError(f"Строка {number}: артикул повторяется в файле.")
            seen.add(article)
            instance = Product.objects.filter(article=article).first()
            if instance and not can_change:
                raise ValidationError(f"Строка {number}: нет прав на изменение существующего товара.")
            try:
                for flag in FLAGS:
                    row[flag] = parse_flag(row[flag])
            except ValidationError as error:
                raise ValidationError(f"Строка {number}: {error.messages[0]}") from error
            form = ProductRowForm(row, instance=instance)
            if not form.is_valid():
                raise ValidationError([f"Строка {number}, {field}: {error}"
                                       for field, errors in form.errors.items() for error in errors])
            instances.append(form.save(commit=False))
        if not instances:
            raise ValidationError("Файл не содержит товаров.")
        for instance in instances:
            instance.save()
        return len(instances)
    except (UnicodeError, csv.Error) as error:
        raise ValidationError("Невозможно прочитать CSV в кодировке UTF-8.") from error


def csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_products(response, products):
    writer = csv.writer(response)
    writer.writerow(FIELDS)
    for product in products.iterator():
        writer.writerow(csv_cell(getattr(product, field)) for field in FIELDS)
