# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_THEME_BASE=light

# Install system dependencies and Chrome
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    gnupg \
    git \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set display port to avoid crash
ENV DISPLAY=:99

# Create non-root user
RUN useradd -m -s /bin/bash streamlit_user && \
    mkdir -p /app && \
    chown -R streamlit_user:streamlit_user /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER streamlit_user

# Copy requirements first for better caching
COPY --chown=streamlit_user:streamlit_user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY --chown=streamlit_user:streamlit_user . .

# Create necessary directories with correct permissions
RUN mkdir -p credentials && \
    mkdir -p analysis_temp && \
    mkdir -p ~/.config/google-chrome && \
    mkdir -p ~/.streamlit

# Create Streamlit config
RUN echo '\
[general]\n\
email = ""\n\
showWarningOnDirectExecution = false\n\
\n\
[server]\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
serverAddress = "0.0.0.0"\n\
serverPort = 8501\n\
' > ~/.streamlit/config.toml

# Expose Streamlit port
EXPOSE 8501

# Set Streamlit specific environment variables
ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# Command to run Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"] 