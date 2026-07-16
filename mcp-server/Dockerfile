FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*



RUN pip install --no-cache-dir fastmcp redis

COPY main.py .

EXPOSE 8001

CMD ["python", "main.py"]
