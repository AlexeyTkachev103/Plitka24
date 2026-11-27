FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_DATA_DIR=/var/lib/plitka24
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && groupadd --gid 10001 shop \
    && useradd --uid 10001 --gid 10001 --no-create-home shop \
    && install -d -o shop -g shop "$DJANGO_DATA_DIR"

COPY manage.py .
COPY ceram24 ceram24
COPY shop shop
COPY static static
COPY examples/products.csv examples/products.csv
COPY scripts/entrypoint.sh /usr/local/bin/plitka24-entrypoint
RUN DJANGO_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))') \
    python manage.py collectstatic --noinput

USER shop
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/usr/local/bin/plitka24-entrypoint"]
CMD ["gunicorn", "ceram24.wsgi:application", "--bind=0.0.0.0:8000", "--workers=2", "--no-control-socket", "--access-logfile=-"]
