# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    PORT=8501 \
    RAILWAY_ENVIRONMENT=production \
    DEBIAN_FRONTEND=noninteractive

# Create a non-root user
RUN useradd -m -s /bin/bash app_user

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    gnupg2 \
    git \
    libmagic1 \
    libpython3-dev \
    build-essential \
    python3-dev \
    pkg-config \
    curl \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    default-jdk \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and ChromeDriver
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1) \
    && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -q --continue -P /chromedriver "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip /chromedriver/chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm /chromedriver/chromedriver_linux64.zip \
    && chmod +x /usr/local/bin/chromedriver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /chromedriver

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip/*

# Create directories and set permissions
RUN mkdir -p /home/app_user/.streamlit \
    /home/app_user/.cache/yt-dlp \
    /home/app_user/.cache/youtube-dl \
    /home/app_user/.cache/selenium \
    credentials \
    analysis_temp \
    sample_generated_videos \
    /home/app_user/.config/google-chrome

# Copy Streamlit config
COPY .streamlit/config.toml /home/app_user/.streamlit/config.toml

# Copy the entire application
COPY . .

# Set proper permissions
RUN chown -R app_user:app_user /app \
    /home/app_user/.streamlit \
    /home/app_user/.cache \
    /home/app_user/.config \
    credentials \
    analysis_temp \
    sample_generated_videos \
    /usr/local/bin/chromedriver && \
    chmod -R 755 /app pipeline && \
    chmod -R 777 credentials \
    analysis_temp \
    sample_generated_videos \
    /home/app_user/.config \
    /home/app_user/.streamlit \
    /home/app_user/.cache \
    /usr/local/bin/chromedriver

# Switch to non-root user
USER app_user

# Set Chrome and Selenium configuration for non-root user
ENV HOME=/home/app_user \
    CHROME_BIN=/usr/bin/google-chrome \
    DISPLAY=:99 \
    PYTHONPATH=${PYTHONPATH}:/app \
    SELENIUM_CACHE_PATH=/home/app_user/.cache/selenium

# Set Streamlit specific environment variables
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# Expose the port that will be used by Streamlit
EXPOSE ${PORT:-8501}

# Start Xvfb and run Streamlit
CMD Xvfb :99 -screen 0 1280x1024x24 -ac +extension GLX +render -noreset & \
    streamlit run --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.maxUploadSize=50 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    streamlit_app.py 