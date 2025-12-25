#Use a recent Python version compatible with all modern packages
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# 1. Install System Dependencies (Chromium + Driver)
# We install chromium-driver here so it matches the browser version exactly
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Python Setup
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Project Files
COPY . .

# Set the command to run your tester.py script
CMD ["gunicorn", "--workers", "3", "--timeout", "120", "--bind", "0.0.0.0:8000", "app:app"]
