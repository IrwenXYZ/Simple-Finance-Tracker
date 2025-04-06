# Use Python 3.12 as the base image
FROM python:3.12-bookworm

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./ /app

# Create a volume mount point for data
VOLUME /app

# Run the bot
CMD ["python", "main.py"]
