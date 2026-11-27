#!/usr/bin/env python
"""
Точка входа для административных задач Django.
Стандартный файл, генерируемый командой `django-admin startproject`.
"""

import os
import sys


def main():
    """Запуск административных команд Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ceram24.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что Django "
            "установлен и доступен в PYTHONPATH. Возможно, вы забыли "
            "активировать виртуальное окружение?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()