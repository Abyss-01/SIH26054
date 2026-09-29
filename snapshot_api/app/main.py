"""AERIS Snapshot API — thin wrapper around the SIH26054 Demo engine."""

import os
from contextlib import asynccontextmanager

from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import Scenario, SnapshotRequest, SnapshotResponse
from .engine import build_snapshot, available_scenarios

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]

# Vercel assigns a unique HTTPS origin to production deployments and previews.
# Permit those origins by default so the static React demo can reach this public
# API without a CORS failure. Set ALLOWED_ORIGIN_REGEX to override this policy.
ALLOWED_ORIGIN_REGEX = os.getenv(
    "ALLOWED_ORIGIN_REGEX", r"^https://[a-z0-9-]+\.vercel\.app$"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to initialise (the engine is stateless).
    yield
    # Shutdown: nothing to clean up.


api = FastAPI(
    title="AERIS Snapshot API",
    description="Synthetic UAV engine telemetry for the SIH26054 demo. "
    "Generates 30-second sensor windows from the existing Demo engine.",
    version="1.0.0",
    lifespan=lifespan,
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@api.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "AERIS Snapshot API"}


@api.get("/api/scenarios", response_model=List[str])
async def list_scenarios() -> List[str]:
    """All scenario keys the engine accepts, including the Auto guided tour."""
    return available_scenarios()


@api.post("/api/snapshot", response_model=SnapshotResponse, status_code=200)
async def generate_snapshot(request: SnapshotRequest) -> Dict[str, Any]:
    """Generate a 30-second telemetry window for the given mission parameters."""
    try:
        return build_snapshot(
            scenario=request.scenario.value,
            noise_level=request.noise_level,
            sample_seed=request.sample_seed,
            flight_distance=request.flight_distance,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Engine error: {error}") from error
