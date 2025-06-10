FROM python:3.11-slim

COPY . /app
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
