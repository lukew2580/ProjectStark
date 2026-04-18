"""
Integration Tests — Full Frontend ↔ Backend Communication
These tests require a running backend server at TEST_BACKEND_URL.
Skip by default; enable with: RUN_INTEGRATION_TESTS=1 pytest tests/integration/
"""
import pytest
import httpx
import os

# Skip all tests in this module unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to run"
)

BACKEND_URL = os.getenv("TEST_BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("TEST_FRONTEND_URL", "http://localhost:3000")


@pytest.fixture(scope="module")
def backend_server():
    """Start the backend server for integration tests."""
    # In real CI, this would use docker-compose up
    # For local dev, assume backend already running
    yield BACKEND_URL
    # No cleanup needed if externally managed


class TestBackendIntegration:
    """Test backend API endpoints used by frontend."""

    def test_health_endpoint(self, backend_server):
        response = httpx.get(f"{backend_server}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("operational", "healthy")

    def test_legacy_chat_endpoint(self, backend_server):
        """Test old /chat endpoint for backward compatibility."""
        response = httpx.post(
            f"{backend_server}/chat",
            json={"question": "Hello world"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_v1_chat_completions(self, backend_server):
        """Test new OpenAI-compatible chat endpoint."""
        response = httpx.post(
            f"{backend_server}/v1/chat/completions",
            json={
                "model": "hardwareless-core",
                "messages": [{"role": "user", "content": "Say hello"}],
                "stream": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]

    def test_v1_stats_endpoint(self, backend_server):
        """Test metrics endpoint consumed by SwarmStatsCard."""
        response = httpx.get(f"{backend_server}/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "total_packets_processed" in data
        assert "swarm_stability" in data
        # Security sub-object
        assert "security" in data
        assert "audit_events_total" in data["security"]

    def test_v1_vector_endpoint(self, backend_server):
        """Test vector encoding used by VectorVisualizer."""
        response = httpx.get(
            f"{backend_server}/v1/vector",
            params={"text": "test", "samples": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "vector" in data
        assert isinstance(data["vector"], list)
        assert len(data["vector"]) > 0


class TestFrontendIntegration:
    """Test that frontend can reach backend (when both running)."""

    def test_frontend_serves(self):
        """Check frontend is up (if running)."""
        response = httpx.get(FRONTEND_URL, timeout=5.0)
        assert response.status_code in (200, 404)

    def test_frontend_can_call_backend(self):
        """Simulate frontend fetch to backend API."""
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        assert response.status_code == 200


class TestDockerCompose:
    """Test docker-compose configuration validity."""

    def test_docker_compose_exists(self):
        compose_file = Path("docker-compose.yml")
        assert compose_file.exists(), "docker-compose.yml missing"

    def test_docker_compose_valid_yaml(self):
        import yaml
        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            yaml.safe_load(f)
        # If we get here, YAML is valid

    def test_frontend_dockerfile_exists(self):
        dockerfile = Path("frontend/Dockerfile")
        assert dockerfile.exists(), "frontend/Dockerfile missing"

    def test_backend_dockerfile_exists(self):
        dockerfile = Path("Dockerfile")
        assert dockerfile.exists(), "Backend Dockerfile missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
