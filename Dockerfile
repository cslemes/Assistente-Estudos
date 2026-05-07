FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libreoffice \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-cpu.txt .
RUN pip install --no-cache-dir -r requirements-cpu.txt

# Install Playwright Chromium for Google Forms scraping
RUN playwright install chromium --with-deps || true

COPY app/ ./app/
COPY main.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]
