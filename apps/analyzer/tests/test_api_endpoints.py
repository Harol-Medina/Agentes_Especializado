"""Unit tests for the analysis API endpoints (task 4.8).

Tests:
- POST /analyze — accepts request, returns 202, stores job
- GET /jobs/{job_id} — returns status from job store, 404 for missing
- WebhookAdapter — HMAC signing, retry logic
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.job_store import jobs
from src.api.schemas import AnalyzeRequest
from src.domain.models.agent_result import AgentResult, AgentStatus
from src.domain.models.analysis_job import AnalysisJob, JobStatus
from src.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_job_store():
    """Ensure job store is clean before and after each test."""
    jobs.clear()
    yield
    jobs.clear()


@pytest.fixture
def job_id():
    return uuid4()


@pytest.fixture
def sample_job(job_id):
    """Pre-populated job with some agent results."""
    job = AnalysisJob(
        id=job_id,
        repo_url="https://github.com/owner/repo",
        status=JobStatus.ANALYZING,
        current_agent="architecture_agent",
        created_at=datetime.now(timezone.utc),
        agent_results=[
            AgentResult(
                agent_name="repository_agent",
                status=AgentStatus.COMPLETED,
                execution_order=1,
            ),
            AgentResult(
                agent_name="architecture_agent",
                status=AgentStatus.RUNNING,
                execution_order=2,
            ),
        ],
    )
    jobs[job_id] = job
    return job


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests: POST /analyze
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_analyze_returns_202(client, job_id):
    """POST /analyze should return 202 with the job_id and pending status."""
    payload = {
        "repo_url": "https://github.com/spring-projects/spring-petclinic",
        "job_id": str(job_id),
        "webhook_url": "http://backend:8080/api/webhooks/analysis-complete",
    }

    response = await client.post("/analyze", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "pending"
    assert "estimated_duration" in data


@pytest.mark.asyncio
async def test_post_analyze_stores_job(client, job_id):
    """POST /analyze should store the job in the in-memory job store."""
    payload = {
        "repo_url": "https://github.com/owner/repo",
        "job_id": str(job_id),
        "webhook_url": "http://backend:8080/api/webhooks/analysis-complete",
    }

    await client.post("/analyze", json=payload)

    assert job_id in jobs
    assert jobs[job_id].repo_url == "https://github.com/owner/repo"
    assert jobs[job_id].status == JobStatus.PENDING


@pytest.mark.asyncio
async def test_post_analyze_validates_request(client):
    """POST /analyze should return 422 for invalid payload."""
    payload = {"repo_url": "not-a-url"}  # missing required fields

    response = await client.post("/analyze", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests: GET /jobs/{job_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_status_returns_progress(client, sample_job, job_id):
    """GET /jobs/{id} should return full job status with agent progress."""
    response = await client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "analyzing"
    assert data["current_agent"] == "architecture_agent"
    assert "repository_agent" in data["progress"]["completed_agents"]


@pytest.mark.asyncio
async def test_get_job_status_404_for_unknown_job(client):
    """GET /jobs/{id} should return 404 for non-existent job."""
    unknown_id = uuid4()
    response = await client.get(f"/jobs/{unknown_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_includes_error_on_failure(client, job_id):
    """GET /jobs/{id} should include error_message for failed jobs."""
    job = AnalysisJob(
        id=job_id,
        repo_url="https://github.com/owner/repo",
        status=JobStatus.FAILED,
        error_message="Clone failed: repository not found",
        created_at=datetime.now(timezone.utc),
    )
    jobs[job_id] = job

    response = await client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Clone failed: repository not found"


# ---------------------------------------------------------------------------
# Tests: WebhookAdapter — HMAC signing
# ---------------------------------------------------------------------------


class TestWebhookAdapter:
    """Tests for the WebhookAdapter HMAC signing logic."""

    def test_sign_payload_produces_valid_hmac(self):
        """_sign_payload should produce a valid HMAC-SHA256 hex digest."""
        from src.adapters.webhook_adapter import WebhookAdapter

        adapter = WebhookAdapter(
            webhook_url="http://backend:8080/webhook",
            webhook_secret="test_secret",
        )

        payload = b'{"jobId":"123","status":"completed"}'
        signature = adapter._sign_payload(payload)

        # Verify by computing expected HMAC manually
        expected = hmac.new(
            key=b"test_secret",
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        assert signature == expected

    def test_sign_payload_deterministic(self):
        """Same payload + secret should always produce the same signature."""
        from src.adapters.webhook_adapter import WebhookAdapter

        adapter = WebhookAdapter(
            webhook_url="http://backend:8080/webhook",
            webhook_secret="my_secret",
        )

        payload = b'{"key":"value"}'
        sig1 = adapter._sign_payload(payload)
        sig2 = adapter._sign_payload(payload)

        assert sig1 == sig2

    @pytest.mark.asyncio
    async def test_notify_completion_sends_signed_request(self):
        """notify_completion should POST with correct headers and signature."""
        from src.adapters.webhook_adapter import WebhookAdapter

        adapter = WebhookAdapter(
            webhook_url="http://backend:8080/webhook",
            webhook_secret="secret123",
        )

        payload = {"jobId": "abc", "status": "completed"}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        expected_sig = hmac.new(
            key=b"secret123",
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = lambda: None
            mock_post.return_value = mock_response

            await adapter.notify_completion(payload)

            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert headers["X-Webhook-Signature"] == f"sha256={expected_sig}"

    @pytest.mark.asyncio
    async def test_notify_completion_retries_on_failure(self):
        """notify_completion should retry up to 3 times on network error."""
        from src.adapters.webhook_adapter import WebhookAdapter

        adapter = WebhookAdapter(
            webhook_url="http://backend:8080/webhook",
            webhook_secret="secret",
        )

        import httpx

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("connection refused")

            # Should not raise (non-fatal)
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await adapter.notify_completion({"jobId": "x", "status": "done"})

            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_notify_completion_succeeds_on_second_retry(self):
        """If first attempt fails but second succeeds, should stop retrying."""
        from src.adapters.webhook_adapter import WebhookAdapter

        adapter = WebhookAdapter(
            webhook_url="http://backend:8080/webhook",
            webhook_secret="secret",
        )

        import httpx

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                httpx.RequestError("timeout"),
                mock_response,
            ]

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await adapter.notify_completion({"jobId": "x", "status": "done"})

            assert mock_post.call_count == 2
