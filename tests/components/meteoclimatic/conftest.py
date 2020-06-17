"""Meteoclimatic generic test utils."""
import pytest

from tests.async_mock import patch


@pytest.fixture(autouse=True)
def patch_requests():
    """Stub out services that makes requests."""
    patch_client = patch("homeassistant.components.meteoclimatic.MeteoclimaticClient")

    with patch_client:
        yield
