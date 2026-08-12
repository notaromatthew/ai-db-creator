FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Named volumes inherit these permissions on first initialization.
RUN useradd --create-home appuser \
    && mkdir -p /app/uploads /app/projects \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"

CMD ["sh", "-c", "python migrate_database.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
