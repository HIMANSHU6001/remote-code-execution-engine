FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        coreutils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 runner && useradd -u 10001 -g runner -s /bin/false -M runner

WORKDIR /sandbox
USER runner
