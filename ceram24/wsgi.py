"""
Конфигурация WSGI для проекта Plitka24.

Этот файл предоставляет WSGI callable как переменную уровня модуля application.
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ceram24.settings')

application = get_wsgi_application()