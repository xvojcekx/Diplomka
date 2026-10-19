FROM python:3.12-slim

WORKDIR /app

# Systémové závislosti pro Matplotlib
RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Vytvoř složku pro vygenerované obrázky a SQLite databázi
RUN mkdir -p /app/app/static/graphs /app/app/data

# SQLite databáze bude v /app/app/data/graphs.db
# Pro trvalé uložení namapujte volume:
#   docker run -v ./data:/app/app/data ...
VOLUME ["/app/app/data"]

ENV PYTHONPATH=/app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

