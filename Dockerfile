#Use a slim, stable Python image for a smaller final deployment size.

FROM python:3.9-slim

#Set the working directory inside the container.

WORKDIR /app

#Copy requirements and install dependencies first (for fast layer caching).

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copy the main application code into the container.

COPY app.py .

#Define the command that runs when the container starts.

CMD ["python", "app.py"]
