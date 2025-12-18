# Use a recent Python version compatible with all modern packages
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first for faster caching
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# If you need Chrome for selenium/webdriver-manager, install it
RUN apt-get update && apt-get install -y \
    wget unzip chromium \
 && rm -rf /var/lib/apt/lists/*

# Set the command to run your tester.py script
CMD ["python", "sec_pass/tester.py"]

