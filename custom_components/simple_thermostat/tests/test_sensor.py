"""Tests for Simple Thermostat sensors."""
import pytest
from unittest.mock import Mock

from ..sensor import (
    SimpleThermostatControlModeSensor,
    SimpleThermostatErrorSensor,
    SimpleThermostatHeatingBinarySensor,
    SimpleThermostatTRVInternalTempSensor,
    SimpleThermostatTRVTargetTempSensor,
    SimpleThermostatTRVValvePositionSensor,
    SimpleThermostatTRVHeatingBinarySensor,
)
from ..climate import CONTROL_MODE_BINARY_HEAT, CONTROL_MODE_PROPORTIONAL


@pytest.fixture
def mock_climate_entity():
    """Create a mock climate entity."""
    entity = Mock()
    entity.name = "ST Test"
    entity.unique_id = "test_thermostat"
    entity.control_mode = CONTROL_MODE_PROPORTIONAL
    entity._cur_temp = 20.0
    entity._target_temp = 21.0
    entity._valve_positions = {"number.test_valve": 75.0}
    entity._valve_entities = ["number.test_valve"]
    entity._trv_internal_temps = {0: 19.5}
    entity._trv_target_temps = {0: 21.5}
    entity._trv_names = ["Test Valve"]
    entity._climate_entities = ["climate.test_trv"]
    return entity


class TestControlModeSensor:
    """Test control mode sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatControlModeSensor(mock_climate_entity)

        assert sensor._attr_name == "ST Test Control Mode"
        assert sensor._attr_unique_id == "test_thermostat_control_mode"
        assert sensor._attr_icon == "mdi:thermometer-auto"

    def test_sensor_state(self, mock_climate_entity):
        """Test sensor returns correct state."""
        mock_climate_entity.control_mode = CONTROL_MODE_BINARY_HEAT
        sensor = SimpleThermostatControlModeSensor(mock_climate_entity)

        assert sensor.state == CONTROL_MODE_BINARY_HEAT

    @pytest.mark.asyncio
    async def test_sensor_update(self, mock_climate_entity):
        """Test sensor async_update method."""
        sensor = SimpleThermostatControlModeSensor(mock_climate_entity)

        # Should not raise any errors
        await sensor.async_update()


class TestTemperatureErrorSensor:
    """Test temperature error sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatErrorSensor(mock_climate_entity)

        assert sensor._attr_name == "ST Test Temperature Error"
        assert sensor._attr_unique_id == "test_thermostat_temp_error"
        assert sensor._attr_native_unit_of_measurement == "°C"
        assert sensor._attr_device_class == "temperature"

    def test_sensor_state_positive_error(self, mock_climate_entity):
        """Test sensor returns positive error when room cooler than target."""
        mock_climate_entity._cur_temp = 19.0
        mock_climate_entity._target_temp = 21.5
        sensor = SimpleThermostatErrorSensor(mock_climate_entity)

        # Error = target - current = 21.5 - 19.0 = 2.5
        assert sensor.state == 2.5

    def test_sensor_state_negative_error(self, mock_climate_entity):
        """Test sensor returns negative error when room warmer than target."""
        mock_climate_entity._cur_temp = 22.5
        mock_climate_entity._target_temp = 20.0
        sensor = SimpleThermostatErrorSensor(mock_climate_entity)

        # Error = target - current = 20.0 - 22.5 = -2.5
        assert sensor.state == -2.5

    def test_sensor_state_none_temps(self, mock_climate_entity):
        """Test sensor returns None when temperatures are None."""
        mock_climate_entity._cur_temp = None
        mock_climate_entity._target_temp = 21.0
        sensor = SimpleThermostatErrorSensor(mock_climate_entity)

        assert sensor.state is None


class TestHeatingBinarySensor:
    """Test heating binary sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatHeatingBinarySensor(mock_climate_entity)

        assert sensor._attr_name == "ST Test Heating"
        assert sensor._attr_unique_id == "test_thermostat_heating"
        assert sensor._attr_device_class == "heat"

    def test_sensor_on_when_valve_open(self, mock_climate_entity):
        """Test sensor is ON when any valve position > 0."""
        mock_climate_entity._valve_positions = {
            "number.valve1": 0,
            "number.valve2": 50,
        }
        sensor = SimpleThermostatHeatingBinarySensor(mock_climate_entity)

        assert sensor.is_on == True

    def test_sensor_off_when_all_valves_closed(self, mock_climate_entity):
        """Test sensor is OFF when all valves are 0."""
        mock_climate_entity._valve_positions = {
            "number.valve1": 0,
            "number.valve2": 0,
        }
        sensor = SimpleThermostatHeatingBinarySensor(mock_climate_entity)

        assert sensor.is_on == False

    def test_sensor_off_when_no_valves(self, mock_climate_entity):
        """Test sensor is OFF when no valve positions tracked."""
        mock_climate_entity._valve_positions = {}
        sensor = SimpleThermostatHeatingBinarySensor(mock_climate_entity)

        assert sensor.is_on == False


class TestTRVInternalTempSensor:
    """Test TRV internal temperature sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)

        assert "Test Valve" in sensor._attr_name
        assert "Internal Temp" in sensor._attr_name
        assert sensor._attr_native_unit_of_measurement == "°C"
        assert sensor._attr_device_class == "temperature"

    def test_sensor_state(self, mock_climate_entity):
        """Test sensor returns correct TRV internal temperature."""
        mock_climate_entity._trv_internal_temps = {0: 19.5}
        sensor = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)

        assert sensor.state == 19.5

    def test_sensor_state_missing(self, mock_climate_entity):
        """Test sensor returns None when TRV temp not available."""
        mock_climate_entity._trv_internal_temps = {}
        sensor = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)

        assert sensor.state is None


class TestTRVTargetTempSensor:
    """Test TRV target temperature sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatTRVTargetTempSensor(mock_climate_entity, 0)

        assert "Test Valve" in sensor._attr_name
        assert "Target Temp" in sensor._attr_name
        assert sensor._attr_native_unit_of_measurement == "°C"
        assert sensor._attr_device_class == "temperature"

    def test_sensor_state(self, mock_climate_entity):
        """Test sensor returns correct TRV target temperature."""
        mock_climate_entity._trv_target_temps = {0: 21.5}
        sensor = SimpleThermostatTRVTargetTempSensor(mock_climate_entity, 0)

        assert sensor.state == 21.5

    def test_sensor_state_missing(self, mock_climate_entity):
        """Test sensor returns None when TRV target not available."""
        mock_climate_entity._trv_target_temps = {}
        sensor = SimpleThermostatTRVTargetTempSensor(mock_climate_entity, 0)

        assert sensor.state is None


class TestTRVValvePositionSensor:
    """Test TRV valve position sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatTRVValvePositionSensor(mock_climate_entity, 0)

        assert "Test Valve" in sensor._attr_name
        assert "Valve Position" in sensor._attr_name
        assert sensor._attr_native_unit_of_measurement == "%"

    def test_sensor_state(self, mock_climate_entity):
        """Test sensor returns correct valve position."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {"number.test_valve": 75.0}
        sensor = SimpleThermostatTRVValvePositionSensor(mock_climate_entity, 0)

        assert sensor.state == 75.0

    def test_sensor_state_zero(self, mock_climate_entity):
        """Test sensor returns 0 when valve closed."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {"number.test_valve": 0}
        sensor = SimpleThermostatTRVValvePositionSensor(mock_climate_entity, 0)

        assert sensor.state == 0

    def test_sensor_state_missing(self, mock_climate_entity):
        """Test sensor returns 0 when valve position not tracked."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {}
        sensor = SimpleThermostatTRVValvePositionSensor(mock_climate_entity, 0)

        assert sensor.state == 0


class TestTRVHeatingBinarySensor:
    """Test per-TRV heating binary sensor."""

    def test_sensor_initialization(self, mock_climate_entity):
        """Test sensor is initialized correctly."""
        sensor = SimpleThermostatTRVHeatingBinarySensor(mock_climate_entity, 0)

        assert "Test Valve" in sensor._attr_name
        assert "Heating" in sensor._attr_name
        assert sensor._attr_device_class == "heat"

    def test_sensor_on_when_valve_open(self, mock_climate_entity):
        """Test sensor is ON when this TRV's valve is open."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {"number.test_valve": 50}
        sensor = SimpleThermostatTRVHeatingBinarySensor(mock_climate_entity, 0)

        assert sensor.is_on == True

    def test_sensor_off_when_valve_closed(self, mock_climate_entity):
        """Test sensor is OFF when this TRV's valve is closed."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {"number.test_valve": 0}
        sensor = SimpleThermostatTRVHeatingBinarySensor(mock_climate_entity, 0)

        assert sensor.is_on == False

    def test_sensor_off_when_valve_missing(self, mock_climate_entity):
        """Test sensor is OFF when valve position not tracked."""
        mock_climate_entity._valve_entities = ["number.test_valve"]
        mock_climate_entity._valve_positions = {}
        sensor = SimpleThermostatTRVHeatingBinarySensor(mock_climate_entity, 0)

        assert sensor.is_on == False


class TestSensorNaming:
    """Test sensor naming with different TRV configurations."""

    def test_single_trv_no_name(self, mock_climate_entity):
        """Test sensor naming with single TRV and no custom name."""
        mock_climate_entity._trv_names = [None]
        sensor = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)

        # Should use "TRV" without index for single TRV
        assert "Trv Internal Temp" in sensor._attr_name

    def test_multiple_trvs_no_names(self, mock_climate_entity):
        """Test sensor naming with multiple TRVs and no custom names."""
        mock_climate_entity._trv_names = [None, None]
        mock_climate_entity._climate_entities = ["climate.trv1", "climate.trv2"]

        sensor1 = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)
        sensor2 = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 1)

        # Should use indexed names (underscore gets converted to space and titlecased)
        assert "Trv 1 Internal Temp" in sensor1._attr_name or "Trv_1 Internal Temp" in sensor1._attr_name
        assert "Trv 2 Internal Temp" in sensor2._attr_name or "Trv_2 Internal Temp" in sensor2._attr_name

    def test_trv_with_custom_name(self, mock_climate_entity):
        """Test sensor naming with custom TRV name."""
        mock_climate_entity._trv_names = ["Hauptventil"]
        sensor = SimpleThermostatTRVInternalTempSensor(mock_climate_entity, 0)

        # Should use custom name
        assert "Hauptventil Internal Temp" in sensor._attr_name
