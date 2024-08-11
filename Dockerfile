FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    xvfb \
    && curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o /tmp/chrome.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /var/log/stock-fetcher && chown -R 1000:1000 /var/log/stock-fetcher

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "/app/stock_fetcher.py"]
