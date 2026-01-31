import os
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import pytest
from eternal_memory.api.main import app

client = TestClient(app)

@pytest.fixture
def mock_env_setup():
    """Setup a temporary directory with 'setting/.env'."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()

    # Change CWD to temp directory
    os.chdir(temp_dir)

    # Create setting directory
    Path("setting").mkdir()

    # Create initial .env
    env_path = Path("setting/.env")
    env_path.write_text("OPENAI_API_KEY=initial_key\n")

    yield temp_dir

    # Cleanup
    os.chdir(original_cwd)
    shutil.rmtree(temp_dir)

def test_set_api_key_valid(mock_env_setup):
    """Test setting a valid API key."""
    response = client.post(
        "/api/settings/api-key",
        params={"provider": "openai", "api_key": "sk-validkey123"}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify .env content
    env_content = Path("setting/.env").read_text()
    assert "OPENAI_API_KEY=sk-validkey123" in env_content

def test_set_api_key_injection_attempt(mock_env_setup):
    """Test that setting an API key with newlines is rejected."""
    malicious_key = "malicious_key\nINJECTED_VAR=hacked"

    response = client.post(
        "/api/settings/api-key",
        params={"provider": "openai", "api_key": malicious_key}
    )

    # This assertion is expected to fail BEFORE the fix
    # We want it to be 400 Bad Request after the fix
    # For now, let's just see what happens. It likely returns 200.
    assert response.status_code == 400
    assert "Invalid API key format" in response.json()["detail"]

    # Verify .env was NOT modified (or at least injection didn't work)
    env_content = Path("setting/.env").read_text()
    assert "INJECTED_VAR=hacked" not in env_content
