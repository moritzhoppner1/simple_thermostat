"""Tests for Simple Thermostat climate entity."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from ..climate import (
    SimpleThermostat,
    PRESET_AWAY,
    PRESET_PRESENT,
    PRESET_COSY,
    PRESET_OFF,
    CONTROL_MODE_BINARY_HEAT,
    CONTROL_MODE_BINARY_COOL,
    CONTROL_MODE_PROPORTIONAL,
    CONTROL_MODE_OFF,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.states.get = Mock(return_value=None)
    hass.services = Mock()
    hass.services.async_call = AsyncMock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()
    return hass


@pytest.fixture
def mock_preset_manager():
    """Create a mock PresetManager."""
    manager = Mock()
    manager.get_active_preset = Mock(return_value=PRESET_PRESENT)
    manager.get_override_status = Mock(return_value={
        "scheduled_preset": None,
        "manual_override": False,
        "presence_override": False,
        "window_open": False,
        "outdoor_temp_high": False,
        "global_away": False,
    })
    manager.set_manual_preset = Mock()
    return manager


@pytest.fixture
def thermostat(mock_hass, mock_preset_manager):
    """Create a SimpleThermostat instance for testing."""
    with patch('custom_components.simple_thermostat.climate.PresetManager', return_value=mock_preset_manager):
        thermo = SimpleThermostat(
            hass=mock_hass,
            name="Test",
            temp_sensor="sensor.test_temp",
            valve_entities=["number.test_valve"],
            climate_entities=["climate.test_trv"],
            away_temp=16.0,
            present_temp=21.0,
            cosy_temp=23.0,
            binary_threshold=0.5,
            hysteresis=0.3,
            sync_remote_temp=False,
            initial_preset=PRESET_PRESENT,
            unique_id="test_thermostat",
            trv_names=["Test Valve"],
            schedule_config=None,
            presence_sensor=None,
            window_sensor=None,
            outdoor_temp_sensor=None,
            global_away_sensor=None,
            presence_away_delay=15,
            outdoor_temp_threshold=20.0,
        )
        return thermo


class TestClimateEntityInitialization:
    """Test climate entity initialization."""

    def test_entity_attributes(self, thermostat):
        """Test entity attributes are set correctly."""
        assert thermostat.name == "ST Test"
        assert thermostat.unique_id == "test_thermostat"
        assert thermostat._temp_sensor == "sensor.test_temp"
        assert thermostat._valve_entities == ["number.test_valve"]
        assert thermostat._climate_entities == ["climate.test_trv"]

    def test_preset_temperatures(self, thermostat):
        """Test preset temperatures are initialized."""
        assert thermostat._away_temp == 16.0
        assert thermostat._present_temp == 21.0
        assert thermostat._cosy_temp == 23.0

    def test_control_parameters(self, thermostat):
        """Test control parameters are initialized."""
        assert thermostat._binary_threshold == 0.5
        assert thermostat._hysteresis == 0.3

    def test_initial_state(self, thermostat):
        """Test initial state is correct."""
        assert thermostat._hvac_mode == HVACMode.OFF
        assert thermostat._enabled == False
        assert thermostat.control_mode == CONTROL_MODE_OFF




class TestControlLogic:
    """Test the hybrid binary + proportional control logic."""

    @pytest.mark.asyncio
    async def test_binary_heat_when_far_below_target(self, thermostat, mock_hass):
        """Test binary heating mode when temp is far below target."""
        thermostat._enabled = True
        thermostat._hvac_mode = HVACMode.HEAT
        thermostat._cur_temp = 18.0
        thermostat._target_temp = 21.0
        # Error = 3.0°C > 0.5°C threshold → binary heat

        await thermostat._async_control_heating()

        assert thermostat.control_mode == CONTROL_MODE_BINARY_HEAT

        # Verify valve set to 100%
        mock_hass.services.async_call.assert_any_call(
            "number",
            "set_value",
            {"entity_id": "number.test_valve", "value": 100},
            blocking=True
        )

        # Verify TRV set to 30°C
        mock_hass.services.async_call.assert_any_call(
            "climate",
            "set_temperature",
            {"entity_id": "climate.test_trv", "temperature": 30},
            blocking=True
        )

    @pytest.mark.asyncio
    async def test_binary_cool_when_far_above_target(self, thermostat, mock_hass):
        """Test binary cooling mode when temp is far above target.

        This is the CRITICAL test case for the bug:
        Room temp 19.8°C, target 16.0°C → should turn OFF heating
        """
        thermostat._enabled = True
        thermostat._hvac_mode = HVACMode.HEAT
        thermostat._cur_temp = 19.8
        thermostat._target_temp = 16.0
        # Error = -3.8°C < -0.5°C threshold → binary cool (OFF)

        await thermostat._async_control_heating()

        assert thermostat.control_mode == CONTROL_MODE_BINARY_COOL

        # Verify valve set to 0%
        mock_hass.services.async_call.assert_any_call(
            "number",
            "set_value",
            {"entity_id": "number.test_valve", "value": 0},
            blocking=True
        )

        # Verify TRV set to 5°C
        mock_hass.services.async_call.assert_any_call(
            "climate",
            "set_temperature",
            {"entity_id": "climate.test_trv", "temperature": 5},
            blocking=True
        )


    @pytest.mark.asyncio
    async def test_no_heating_when_disabled(self, thermostat, mock_hass):
        """Test that no heating occurs when thermostat is disabled."""
        thermostat._enabled = False
        thermostat._cur_temp = 18.0
        thermostat._target_temp = 21.0

        await thermostat._async_control_heating()

        # Should not call any services
        assert not mock_hass.services.async_call.called

    @pytest.mark.asyncio
    async def test_no_heating_when_temps_none(self, thermostat, mock_hass):
        """Test that no heating occurs when temperatures are None."""
        thermostat._enabled = True
        thermostat._cur_temp = None
        thermostat._target_temp = 21.0

        await thermostat._async_control_heating()

        assert not mock_hass.services.async_call.called


class TestValvePositionReading:
    """Test reading valve positions from number entities."""

    @pytest.mark.asyncio
    async def test_read_valve_position(self, thermostat, mock_hass):
        """Test reading valve position from entity."""
        # Mock valve state
        mock_state = Mock()
        mock_state.state = "75"
        mock_hass.states.get.return_value = mock_state

        await thermostat._async_read_valve_positions()

        assert thermostat._valve_positions["number.test_valve"] == 75.0

    @pytest.mark.asyncio
    async def test_read_valve_position_unavailable(self, thermostat, mock_hass):
        """Test handling unavailable valve state."""
        mock_state = Mock()
        mock_state.state = STATE_UNAVAILABLE
        mock_hass.states.get.return_value = mock_state

        await thermostat._async_read_valve_positions()

        # Should not update valve position
        assert "number.test_valve" not in thermostat._valve_positions




class TestExtraStateAttributes:
    """Test extra state attributes exposed to UI."""

    def test_temperature_sensor_attribute(self, thermostat):
        """Test that temperature_sensor is exposed in attributes."""
        attrs = thermostat.extra_state_attributes

        assert "temperature_sensor" in attrs
        assert attrs["temperature_sensor"] == "sensor.test_temp"

    def test_control_mode_attribute(self, thermostat):
        """Test that control_mode is exposed in attributes."""
        thermostat.control_mode = CONTROL_MODE_BINARY_HEAT
        attrs = thermostat.extra_state_attributes

        assert "control_mode" in attrs
        assert attrs["control_mode"] == CONTROL_MODE_BINARY_HEAT

    def test_temperature_error_attribute(self, thermostat):
        """Test that temperature_error is calculated correctly."""
        thermostat._cur_temp = 20.0
        thermostat._target_temp = 21.5

        attrs = thermostat.extra_state_attributes

        assert "temperature_error" in attrs
        assert attrs["temperature_error"] == 1.5

    def test_valve_positions_attribute(self, thermostat):
        """Test that valve_positions are exposed."""
        thermostat._valve_positions = {"number.test_valve": 75.0}

        attrs = thermostat.extra_state_attributes

        assert "valve_positions" in attrs
        assert attrs["valve_positions"]["number.test_valve"] == 75.0
