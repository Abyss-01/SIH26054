# Dockerfile for the AERIS Snapshot API.
# Build from the REPO ROOT so that Demo/ is available alongside snapshot_api/.
# The engine imports "Demo.telemetry.generator", which resolves via PYTHONPATH=/app.
#
#   cd ..
#   docker build -f snapshot_api/Dockerfile -t areis-snapshot-api .
#   docker run -p 8000:8000 -e ALLOWED_ORIGINS="http://localhost:5173" areis-snapshot-api

FROM python:3.11-slim

WORKDIR /app

# The whole repo is the build context, so Demo/ and snapshot_api/ are both here.
COPY . .

# Install only the API's dependencies (the Demo engine's pandas/numpy are shared).
RUN pip install --no-cache-dir -r snapshot_api/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000

# uvicorn target: the "api" FastAPI instance in snapshot_api/app/main.py.
CMD ["uvicorn", "snapshot_api.app.main:api", "--host", "0.0.0.0", "--port", "8000"]
