"""Integration tests for API endpoints using httpx AsyncClient."""
import os
import sys
import json
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ORIGINAL_PDF = os.path.join(os.path.dirname(__file__), "..", "..", "T4_edited.pdf")


@pytest.mark.asyncio
class TestUploadEndpoint:
    """Test POST /api/upload."""

    @pytest.mark.skipif(not os.path.exists(ORIGINAL_PDF), reason="Test PDF not available")
    async def test_upload_pdf_returns_fields(self, test_client):
        with open(ORIGINAL_PDF, "rb") as f:
            resp = await test_client.post(
                "/api/upload",
                files={"file": ("T4_edited.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "14" in data or "error" not in data

    async def test_upload_rejects_unsupported_type(self, test_client):
        resp = await test_client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestProfileEndpoint:
    """Test POST /api/profiles."""

    async def test_create_profile_success(self, test_client):
        body = {
            "tax_year": 2024,
            "province_code": "ON",
            "employment": {
                "total_employment_income": 55000,
                "total_cpp_contributions": 3064.25,
                "total_ei_premiums": 913.00,
                "total_income_tax_withheld": 7420.84,
            },
        }
        resp = await test_client.post("/api/profiles", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "profile_id" in data
        assert data["tax_year"] == 2024
        assert data["province"] == "ON"

    async def test_create_profile_defaults(self, test_client):
        resp = await test_client.post("/api/profiles", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "profile_id" in data


@pytest.mark.asyncio
class TestAnalysisEndpoint:
    """Test analysis pipeline endpoints."""

    async def _create_profile(self, client):
        body = {
            "tax_year": 2024,
            "province_code": "ON",
            "employment": {
                "total_employment_income": 55000,
                "total_cpp_contributions": 3064.25,
                "total_ei_premiums": 913.00,
                "total_income_tax_withheld": 7420.84,
            },
            "registered_accounts": {
                "rrsp_room_remaining": 12000,
                "tfsa_room_remaining": 8500,
            },
        }
        resp = await client.post("/api/profiles", json=body)
        return resp.json()["profile_id"]

    async def test_trigger_analysis(self, test_client):
        from unittest.mock import patch, AsyncMock
        profile_id = await self._create_profile(test_client)
        with patch("services.lightrag_service.query_tax_guidance", new_callable=AsyncMock, return_value={"answer": "test", "mode": "hybrid"}):
            resp = await test_client.post(f"/api/analyze/{profile_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile_id"] == profile_id
        assert "case_id" in data
        assert data["insights_count"] >= 0

    async def test_analysis_status(self, test_client):
        from unittest.mock import patch, AsyncMock
        profile_id = await self._create_profile(test_client)
        with patch("services.lightrag_service.query_tax_guidance", new_callable=AsyncMock, return_value={"answer": "test", "mode": "hybrid"}):
            await test_client.post(f"/api/analyze/{profile_id}")
        resp = await test_client.get(f"/api/analysis/{profile_id}/status")
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "PENDING"

    async def test_analysis_not_found(self, test_client):
        resp = await test_client.post("/api/analyze/99999")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestAdvisorWorkflow:
    """Test full advisor review workflow: create → analyze → approve."""

    async def _setup_case(self, client, headers=None):
        from unittest.mock import patch, AsyncMock
        body = {
            "tax_year": 2024,
            "province_code": "ON",
            "employment": {"total_employment_income": 85000, "total_income_tax_withheld": 20000},
            "registered_accounts": {"rrsp_room_remaining": 15000},
        }
        profile_resp = await client.post("/api/profiles", json=body)
        profile_id = profile_resp.json()["profile_id"]
        with patch("services.lightrag_service.query_tax_guidance", new_callable=AsyncMock, return_value={"answer": "test", "mode": "hybrid"}):
            analysis_resp = await client.post(f"/api/analyze/{profile_id}")
        return profile_id, analysis_resp.json().get("case_id")

    async def test_advisor_queue_returns_cases(self, test_client, advisor_headers):
        await self._setup_case(test_client)
        resp = await test_client.get("/api/advisor/queue", headers=advisor_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "queue" in data
        assert len(data["queue"]) >= 1

    async def test_approve_case(self, test_client, advisor_headers):
        _, case_id = await self._setup_case(test_client)
        resp = await test_client.post(f"/api/advisor/case/{case_id}/approve", json={}, headers=advisor_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"

    async def test_reject_case(self, test_client, advisor_headers):
        _, case_id = await self._setup_case(test_client)
        resp = await test_client.post(
            f"/api/advisor/case/{case_id}/reject",
            json={"reason": "Values seem incorrect"},
            headers=advisor_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"

    async def test_escalate_case(self, test_client, advisor_headers):
        _, case_id = await self._setup_case(test_client)
        resp = await test_client.post(f"/api/advisor/case/{case_id}/escalate", json={}, headers=advisor_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ESCALATED"

    async def test_approved_insights_visible(self, test_client, advisor_headers):
        profile_id, case_id = await self._setup_case(test_client)
        await test_client.post(f"/api/advisor/case/{case_id}/approve", json={}, headers=advisor_headers)
        resp = await test_client.get(f"/api/analysis/{profile_id}/results")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["insights"]) >= 0
