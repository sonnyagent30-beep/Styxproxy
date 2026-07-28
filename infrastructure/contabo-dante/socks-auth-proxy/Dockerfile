FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY app.py .

RUN useradd -m -u 1000 socksauth

EXPOSE 1081

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:9000/health || nc -z localhost 1081 || exit 1

CMD ["python", "-u", "app.py"]
