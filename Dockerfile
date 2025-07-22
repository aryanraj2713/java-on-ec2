FROM openjdk:17-jdk-slim as builder

RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY deployment_script.py /usr/local/bin/deployment_script.py
RUN chmod +x /usr/local/bin/deployment_script.py

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

FROM openjdk:17-jdk-slim

RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    python3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY --from=builder /usr/local/bin/deployment_script.py /usr/local/bin/deployment_script.py
RUN chmod +x /usr/local/bin/deployment_script.py

RUN mkdir -p /home/appuser/.ssh && \
    chown -R appuser:appuser /home/appuser/.ssh && \
    chmod 700 /home/appuser/.ssh

USER appuser

RUN mkdir -p /app && chown appuser:appuser /app

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

CMD ["python3", "/usr/local/bin/deployment_script.py", "--help"]

LABEL maintainer="deployment-team"
LABEL version="1.0"
LABEL description="Java application deployment container" 