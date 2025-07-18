# If you MUST use Buster, manually build libolm
FROM python:3.10-slim-buster

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install build dependencies first
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Manually build and install libolm3 (this is what's missing in Buster)
RUN git clone -b 3.2.16 https://gitlab.matrix.org/matrix-org/olm.git /tmp/olm \
    && cd /tmp/olm \
    && cmake . -DCMAKE_INSTALL_PREFIX=/usr \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && rm -rf /tmp/olm

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY boo_bot.py .
COPY tests/ tests/
COPY config/ config/
COPY config.py .
COPY config_manager.py .
COPY utils/ utils/
COPY plugins/ plugins/
# Copy root-level test files
COPY test_*.py ./

# Create directories
RUN mkdir -p bot_store temp_media test_store logs && \
    chmod 777 bot_store temp_media test_store logs

# Default command runs the bot
CMD ["python", "-u", "boo_bot.py"]

# Alternative command to run tests
# docker-compose run --rm boo_bot pytest tests/