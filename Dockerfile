# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=8501

# Create a non-root user
RUN useradd -m -s /bin/bash app_user

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    gnupg \
    git \
    libmagic1 \
    libpython3-dev \
    build-essential \
    python3-dev \
    pkg-config \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create directories and set permissions
RUN mkdir -p /home/app_user/.streamlit \
    /home/app_user/.cache/yt-dlp \
    /home/app_user/.cache/youtube-dl \
    credentials \
    analysis_temp \
    /home/app_user/.config/google-chrome

# Copy Streamlit config
COPY .streamlit/config.toml /home/app_user/.streamlit/config.toml

# Copy the entire application
COPY . .

# Set proper permissions
RUN chown -R app_user:app_user /app \
    /home/app_user/.streamlit \
    /home/app_user/.cache \
    credentials \
    analysis_temp \
    /home/app_user/.config && \
    chmod -R 755 /app pipeline && \
    chmod -R 777 credentials \
    analysis_temp \
    /home/app_user/.config \
    /home/app_user/.streamlit \
    /home/app_user/.cache

# Switch to non-root user
USER app_user

# Set Chrome configuration for non-root user
ENV HOME=/home/app_user \
    CHROME_BIN=/usr/bin/google-chrome \
    DISPLAY=:99

# Set Streamlit specific environment variables
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Expose the port that will be used by Streamlit
EXPOSE ${PORT:-8501}

# Command to run Streamlit using PORT environment variable
CMD streamlit run streamlit_app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 