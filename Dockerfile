FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Statiques collectés dans l'image, servis par whitenoise
RUN python manage.py collectstatic --noinput

RUN chmod +x deploy/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["deploy/entrypoint.sh"]
CMD ["uvicorn", "PlantesManager.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
