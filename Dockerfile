FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY redactagent redactagent
COPY web web
COPY policies policies
COPY data/samples data/samples
ENV RA_RUNS_DIR=/data/runs
EXPOSE 8080
CMD ["python", "-c", "import uvicorn; uvicorn.run('redactagent.server:app', host='0.0.0.0', port=8080)"]
