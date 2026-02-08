"""Test fixtures for Simple Thermostat."""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from homeassistant.core import HomeAssistant, State


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    return hass


@pytest.fixture
def mock_state():
    """Create a mock state object factory."""
    def _create_state(entity_id: str, state: str, attributes: dict = None):
        mock = Mock(spec=State)
        mock.entity_id = entity_id
        mock.state = state
        mock.attributes = attributes or {}
        return mock
    return _create_state


@pytest.fixture
def basic_schedule_config():
    """Basic schedule configuration for testing."""
    return {
        "weekday": [
            {"time": "06:00", "preset": "present"},
            {"time": "08:00", "preset": "away"},
            {"time": "17:00", "preset": "present"},
            {"time": "22:00", "preset": "cosy"},
        ],
        "weekend": [
            {"time": "08:00", "preset": "present"},
            {"time": "23:00", "preset": "cosy"},
        ],
    }


@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime.now() for testing."""
    class MockDatetime:
        _now = datetime(2024, 1, 15, 12, 0)  # Monday, Jan 15, 2024, 12:00 PM

        @classmethod
        def now(cls):
            return cls._now

        @classmethod
        def set_time(cls, dt: datetime):
            cls._now = dt

    monkeypatch.setattr("custom_components.simple_thermostat.preset_manager.datetime", MockDatetime)
    return MockDatetime
