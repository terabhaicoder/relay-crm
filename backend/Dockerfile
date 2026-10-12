FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-local.txt ./
RUN pip install --no-cache-dir -r requirements-local.txt
COPY app ./app
COPY migrations ./migrations
COPY local_migrations ./local_migrations
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 erp && mkdir /data && chown -R erp:erp /app /data
USER erp
ENV DATABASE_URL="sqlite:////data/crm.db"
ENV UPLOAD_DIR="/data/uploads"
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
