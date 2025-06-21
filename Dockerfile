FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Extra safety net: manually ensure critical packages are installed
# RUN pip install --no-cache-dir fastapi uvicorn[standard] serpapi google-search-results pydantic pymongo python-dotenv requests

# ✅ Copy environment variables
COPY .env .

# ✅ Copy your application code
COPY . .

# Use non-root user for safety
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Run the FastAPI server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
