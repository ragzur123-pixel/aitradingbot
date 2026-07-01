# AiTradingBot: Pro-Grade Hardening Docker Environment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p chroma_db final_memory transcripts logs

# Environment variables (Defaults - Override in .env or docker-compose)
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# Main entry point: Master Orchestrator
CMD ["python", "master_orchestrator.py"]
