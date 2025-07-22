FROM openjdk:17-jre-slim

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /app /home/appuser/.ssh \
    && chown -R appuser:appuser /app /home/appuser/.ssh \
    && chmod 700 /home/appuser/.ssh

# Copy requirements first for better caching
COPY requirements-docker.txt /tmp/requirements-docker.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /tmp/requirements-docker.txt \
    && rm /tmp/requirements-docker.txt

WORKDIR /app

# Copy application files
COPY deployment_script.py logfire_config.py secrets_manager.py /usr/local/bin/
RUN chmod +x /usr/local/bin/deployment_script.py

USER appuser

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

CMD ["python3", "/usr/local/bin/deployment_script.py", "--help"]

LABEL maintainer="deployment-team"
LABEL version="1.0"
LABEL description="Java application deployment container" 