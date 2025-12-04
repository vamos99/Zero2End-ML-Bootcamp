# Base Image (Bookworm is newer and often has fewer CVEs than Bullseye)
FROM python:3.10-slim-bookworm

# Working Directory
WORKDIR /app

# Install System Dependencies & Security Updates
# apt-get upgrade -y fixes known vulnerabilities in system packages
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Requirements
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
COPY . .

# Expose Ports (8000 for API, 8501 for Streamlit)
EXPOSE 8000
EXPOSE 8501

# Default Command (Overridden in docker-compose)
CMD ["bash"]
