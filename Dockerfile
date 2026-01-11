# Base image
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (QuantLib needs build tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libquantlib0-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copy project files
COPY . .

# Expose Dash port
EXPOSE 8050

# Use Gunicorn with 4 workers for production
CMD ["gunicorn", "rates:server", "--bind", "0.0.0.0:8050", "--workers", "4", "--worker-class", "gthread"]
