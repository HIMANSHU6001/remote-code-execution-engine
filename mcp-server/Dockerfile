FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastmcp redis

COPY main.py .

EXPOSE 8001

CMD ["python", "main.py"]
