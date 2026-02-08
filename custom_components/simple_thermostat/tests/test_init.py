"""Tests for Simple Thermostat integration setup."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .. import (
    async_setup,
    DOMAIN,
    SERVICE_SET_PRESET_TEMPERATURE,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.http = Mock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.services = Mock()
    hass.services.async_register = Mock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {}


class TestIntegrationSetup:
    """Test integration setup."""

    @pytest.mark.asyncio
    async def test_async_setup_success(self, mock_hass, mock_config):
        """Test successful integration setup."""
        result = await async_setup(mock_hass, mock_config)

        assert result == True

    @pytest.mark.asyncio
    async def test_service_registration(self, mock_hass, mock_config):
        """Test that set_preset_temperature service is registered."""
        await async_setup(mock_hass, mock_config)

        mock_hass.services.async_register.assert_called_once()
        call_args = mock_hass.services.async_register.call_args

        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == SERVICE_SET_PRESET_TEMPERATURE

    @pytest.mark.asyncio
    async def test_www_path_registration(self, mock_hass, mock_config):
        """Test that custom card www path is registered."""
        with patch('pathlib.Path.exists', return_value=True):
            await async_setup(mock_hass, mock_config)

            # Verify static path was registered
            mock_hass.http.async_register_static_paths.assert_called_once()


class TestSetPresetTemperatureService:
    """Test the set_preset_temperature service.

    Note: The service handler is created inside async_setup(), so we test
    indirectly by verifying the service gets registered correctly.
    """

    @pytest.mark.asyncio
    async def test_service_handler_registered(self, mock_hass, mock_config):
        """Test that the service handler is registered with correct signature."""
        await async_setup(mock_hass, mock_config)

        # Verify service was registered
        assert mock_hass.services.async_register.called

        # Get the registered handler
        call_args = mock_hass.services.async_register.call_args
        domain, service, handler, schema = call_args[0][0], call_args[0][1], call_args[0][2], call_args[1]["schema"]

        assert domain == DOMAIN
        assert service == SERVICE_SET_PRESET_TEMPERATURE
        assert callable(handler)
        assert schema is not None


class TestWWWPathRegistration:
    """Test custom card www path registration."""

    @pytest.mark.asyncio
    async def test_www_path_exists(self, mock_hass, mock_config):
        """Test registration when www path exists."""
        with patch('pathlib.Path.exists', return_value=True):
            await async_setup(mock_hass, mock_config)

            mock_hass.http.async_register_static_paths.assert_called_once()

            # Check the path configuration
            call_args = mock_hass.http.async_register_static_paths.call_args
            paths = call_args[0][0]
            assert len(paths) == 1
            assert paths[0].url_path == "/simple_thermostat"

    @pytest.mark.asyncio
    async def test_www_path_not_exists(self, mock_hass, mock_config):
        """Test when www path doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            await async_setup(mock_hass, mock_config)

            # Should still succeed but log warning
            mock_hass.http.async_register_static_paths.assert_not_called()
