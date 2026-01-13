# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
RUN pip install pyserial

# Copy your project files into the container
# COPY . /app

# Expose port if you plan to use Wi-Fi adapters
EXPOSE 8000

# Default command to run your script
# CMD ["python", "main.py"]
