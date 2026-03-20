FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        clang \
        coreutils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root runner user
RUN groupadd -g 10001 runner && useradd -u 10001 -g runner -s /bin/false -M runner

WORKDIR /sandbox
USER runner
