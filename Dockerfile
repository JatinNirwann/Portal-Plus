FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install packages one by one to identify issues
RUN pip install --no-cache-dir python-telegram-bot==20.6
RUN pip install --no-cache-dir python-dotenv==1.0.0
RUN pip install --no-cache-dir requests==2.31.0
RUN pip install --no-cache-dir schedule==1.2.0
RUN pip install --no-cache-dir httpx==0.24.1

# Try to install pyjiit with git (in case PyPI version has issues)
RUN pip install --no-cache-dir git+https://github.com/codelif/pyjiit.git || \
    pip install --no-cache-dir pyjiit

COPY . .

CMD ["python", "src/main.py"]