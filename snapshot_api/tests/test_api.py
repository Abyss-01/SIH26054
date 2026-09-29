"""Basic contract tests for the snapshot API."""

import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient, ASGITransport

# The API imports the Demo engine, so it must run with the repo root on the
# Python path. Pytest adds the snapshot_api directory by default; we add the
# parent here so `Demo.telemetry.generator` resolves.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))  # noqa: E402

from app.main import api  # noqa: E402


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client against the FastAPI app (in-process, no server needed)."""
    transport = ASGITransport(app=api)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def demo_scenarios() -> list[str]:
    from Demo.config.scenarios import SCENARIO_OPTIONS
    return list(SCENARIO_OPTIONS)


class TestHealth:
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "AERIS Snapshot API"


class TestScenarios:
    async def test_scenarios(self, client: AsyncClient, demo_scenarios: list[str]) -> None:
        resp = await client.get("/api/scenarios")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert "Auto (Follow Flight Profile Stages)" in body
        assert "Nominal Operation (No Anomaly)" in body
        assert len(body) == len(demo_scenarios)


class TestSnapshot:
    async def test_nominal_cruise(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "Nominal Operation (No Anomaly)",
                "noise_level": 1.0,
                "sample_seed": 42,
                "flight_distance": 140.0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["scenario"] == "Nominal Operation (No Anomaly)"
        assert body["meta"]["flight_stage"] == "4. Cruise"
        assert body["meta"]["flight_distance_km"] == 140.0
        assert body["meta"]["seed"] == 42
        assert body["health"]["score"] >= 95  # nominal should score high
        assert body["health"]["status"] == "NORMAL"
        assert len(body["channels"]["columns"]) >= 10
        assert len(body["channels"]["observed"]) == 30
        assert len(body["channels"]["baseline"]) == 30
        assert len(body["anomaly"]["scores"]) == 30
        assert len(body["anomaly"]["mask"]) == 30
        assert isinstance(body["reference_bands"], dict)
        assert body["rul"] is None

    async def test_fuel_pressure_instability(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)",
                "noise_level": 1.0,
                "sample_seed": 42,
                "flight_distance": 140.0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["scenario"].startswith("1. Fuel Pressure")
        assert body["channels"]["observed"][0]["Fuel Pressure (bar)"] is not None

    async def test_guided_tour_auto(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "Auto (Follow Flight Profile Stages)",
                "noise_level": 1.0,
                "sample_seed": 42,
                "flight_distance": 140.0,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Auto resolves to the stage-appropriate fault.
        assert body["meta"]["scenario"] != "Auto (Follow Flight Profile Stages)"
        assert body["meta"]["requested_scenario"] == "Auto (Follow Flight Profile Stages)"

    async def test_reproducible_seed(self, client: AsyncClient) -> None:
        req = {
            "scenario": "Nominal Operation (No Anomaly)",
            "noise_level": 1.0,
            "sample_seed": 7,
            "flight_distance": 140.0,
        }
        r1 = await client.post("/api/snapshot", json=req)
        r2 = await client.post("/api/snapshot", json=req)
        assert r1.json()["channels"]["observed"] == r2.json()["channels"]["observed"]

    async def test_seedchanges_noise(self, client: AsyncClient) -> None:
        req_a = {
            "scenario": "Nominal Operation (No Anomaly)",
            "noise_level": 1.0,
            "sample_seed": 7,
            "flight_distance": 140.0,
        }
        req_b = {
            "scenario": "Nominal Operation (No Anomaly)",
            "noise_level": 2.0,
            "sample_seed": 7,
            "flight_distance": 140.0,
        }
        a = await client.post("/api/snapshot", json=req_a)
        b = await client.post("/api/snapshot", json=req_b)
        # Same seed, different noise → different samples.
        assert a.json()["channels"]["observed"] != b.json()["channels"]["observed"]

    async def test_bad_scenario(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "Not A Real Scenario",
                "noise_level": 1.0,
                "sample_seed": 42,
                "flight_distance": 140.0,
            },
        )
        assert resp.status_code == 400

    async def test_bad_noise(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "Nominal Operation (No Anomaly)",
                "noise_level": 100.0,
                "sample_seed": 42,
                "flight_distance": 140.0,
            },
        )
        assert resp.status_code == 400

    async def test_bad_distance(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/snapshot",
            json={
                "scenario": "Nominal Operation (No Anomaly)",
                "noise_level": 1.0,
                "sample_seed": 42,
                "flight_distance": 500.0,
            },
        )
        assert resp.status_code == 400

    async def test_boundary_distances(self, client: AsyncClient) -> None:
        """Each stage boundary should resolve to the documented stage."""
        from Demo.config.scenarios import FLIGHT_STAGES
        cases = (
            (0, FLIGHT_STAGES[0]),
            (20, FLIGHT_STAGES[0]),
            (21, FLIGHT_STAGES[1]),
            (50, FLIGHT_STAGES[1]),
            (110, FLIGHT_STAGES[2]),
            (180, FLIGHT_STAGES[3]),
            (240, FLIGHT_STAGES[4]),
            (280, FLIGHT_STAGES[5]),
            (281, FLIGHT_STAGES[6]),
            (300, FLIGHT_STAGES[6]),
        )
        for distance, expected_stage in cases:
            resp = await client.post(
                "/api/snapshot",
                json={
                    "scenario": "Nominal Operation (No Anomaly)",
                    "noise_level": 0.0,
                    "sample_seed": 1,
                    "flight_distance": float(distance),
                },
            )
            assert resp.status_code == 200
            assert resp.json()["meta"]["flight_stage"] == expected_stage
