# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (ffmpeg and build essentials for bcrypt/psycopg2)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for temp uploads
RUN mkdir -p temp_uploads

# Expose FastAPI port
EXPOSE 8000

# Run the application
ENTRYPOINT ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
