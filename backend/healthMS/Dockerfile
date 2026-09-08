FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py .
COPY healthMS/ healthMS/
COPY hms/ hms/
COPY lis/ lis/
COPY integration/ integration/
COPY templates/ templates/
COPY simulate_integration.py .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "healthMS.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]
