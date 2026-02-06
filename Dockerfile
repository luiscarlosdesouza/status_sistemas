FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment directory for database persistence
VOLUME /app/instance

EXPOSE 5000

# Use Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
