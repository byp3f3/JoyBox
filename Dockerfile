FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN if [ -d /app/joybox/media/products ]; then \
      mkdir -p /app/seed_media && \
      cp -r /app/joybox/media/products /app/seed_media/; \
    fi

WORKDIR /app/joybox

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
