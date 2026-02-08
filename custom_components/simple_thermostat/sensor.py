"""Sensor platform for Simple Thermostat."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import UnitOfTemperature

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Simple Thermostat sensor platform."""
    if discovery_info is None:
        return

    sensors = discovery_info.get("sensors", [])
    sensor_entities = [s for s in sensors if isinstance(s, SensorEntity)]

    if sensor_entities:
        async_add_entities(sensor_entities, update_before_add=True)


def _get_trv_suffix(climate_entity, trv_index):
    """Generate TRV suffix for sensor names."""
    trv_name = climate_entity._trv_names[trv_index] if trv_index < len(climate_entity._trv_names) and climate_entity._trv_names[trv_index] else None
    num_trvs = len(climate_entity._climate_entities)

    if trv_name:
        # Use custom name
        return trv_name.lower().replace(' ', '_')
    elif num_trvs == 1:
        # Only one TRV, no suffix
        return "trv"
    else:
        # Multiple TRVs without names, use index
        return f"trv_{trv_index + 1}"


async def async_create_sensors(hass, climate_entity):
    """Create diagnostic sensors for a climate entity."""
    sensors = []

    # Main control mode sensor
    sensors.append(SimpleThermostatControlModeSensor(climate_entity))

    # Temperature error sensor
    sensors.append(SimpleThermostatErrorSensor(climate_entity))

    # Overall heating binary sensor
    sensors.append(SimpleThermostatHeatingBinarySensor(climate_entity))

    # Per-TRV sensors
    for idx, climate_id in enumerate(climate_entity._climate_entities):
        sensors.append(SimpleThermostatTRVInternalTempSensor(climate_entity, idx))
        sensors.append(SimpleThermostatTRVTargetTempSensor(climate_entity, idx))
        sensors.append(SimpleThermostatTRVValvePositionSensor(climate_entity, idx))
        sensors.append(SimpleThermostatTRVHeatingBinarySensor(climate_entity, idx))

    return sensors


class SimpleThermostatControlModeSensor(SensorEntity):
    """Sensor showing the current control mode."""

    def __init__(self, climate_entity):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._attr_name = f"{climate_entity.name} Control Mode"
        self._attr_unique_id = f"{climate_entity.unique_id}_control_mode"
        self._attr_icon = "mdi:thermometer-auto"

    @property
    def state(self):
        """Return the current control mode."""
        return self._climate_entity.control_mode

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatErrorSensor(SensorEntity):
    """Sensor showing temperature error (target - current)."""

    def __init__(self, climate_entity):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._attr_name = f"{climate_entity.name} Temperature Error"
        self._attr_unique_id = f"{climate_entity.unique_id}_temp_error"
        self._attr_icon = "mdi:delta"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"

    @property
    def state(self):
        """Return the temperature error."""
        if self._climate_entity._cur_temp is None or self._climate_entity._target_temp is None:
            return None
        return round(self._climate_entity._target_temp - self._climate_entity._cur_temp, 2)

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatHeatingBinarySensor(BinarySensorEntity):
    """Binary sensor showing if overall heating is active."""

    def __init__(self, climate_entity):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._attr_name = f"{climate_entity.name} Heating"
        self._attr_unique_id = f"{climate_entity.unique_id}_heating"
        self._attr_icon = "mdi:fire"
        self._attr_device_class = "heat"

    @property
    def is_on(self):
        """Return true if heating."""
        return any(v > 0 for v in self._climate_entity._valve_positions.values())

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatTRVInternalTempSensor(SensorEntity):
    """Sensor showing TRV internal temperature."""

    def __init__(self, climate_entity, trv_index):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._trv_index = trv_index
        trv_suffix = _get_trv_suffix(climate_entity, trv_index)
        self._attr_name = f"{climate_entity.name} {trv_suffix.replace('_', ' ').title()} Internal Temp"
        self._attr_unique_id = f"{climate_entity.unique_id}_{trv_suffix}_internal_temp"
        self._attr_icon = "mdi:thermometer"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"

    @property
    def state(self):
        """Return the TRV internal temperature."""
        return self._climate_entity._trv_internal_temps.get(self._trv_index)

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatTRVTargetTempSensor(SensorEntity):
    """Sensor showing what target temperature was sent to TRV."""

    def __init__(self, climate_entity, trv_index):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._trv_index = trv_index
        trv_suffix = _get_trv_suffix(climate_entity, trv_index)
        self._attr_name = f"{climate_entity.name} {trv_suffix.replace('_', ' ').title()} Target Temp"
        self._attr_unique_id = f"{climate_entity.unique_id}_{trv_suffix}_target_temp"
        self._attr_icon = "mdi:target"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"

    @property
    def state(self):
        """Return the TRV target temperature."""
        return self._climate_entity._trv_target_temps.get(self._trv_index)

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatTRVValvePositionSensor(SensorEntity):
    """Sensor showing TRV valve position."""

    def __init__(self, climate_entity, trv_index):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._trv_index = trv_index
        trv_suffix = _get_trv_suffix(climate_entity, trv_index)
        self._attr_name = f"{climate_entity.name} {trv_suffix.replace('_', ' ').title()} Valve Position"
        self._attr_unique_id = f"{climate_entity.unique_id}_{trv_suffix}_valve_position"
        self._attr_icon = "mdi:valve"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = None

    @property
    def state(self):
        """Return the valve position."""
        valve_entity = self._climate_entity._valve_entities[self._trv_index]
        return self._climate_entity._valve_positions.get(valve_entity, 0)

    async def async_update(self):
        """Update the sensor."""
        pass


class SimpleThermostatTRVHeatingBinarySensor(BinarySensorEntity):
    """Binary sensor showing if this TRV is heating."""

    def __init__(self, climate_entity, trv_index):
        """Initialize the sensor."""
        self._climate_entity = climate_entity
        self._trv_index = trv_index
        trv_suffix = _get_trv_suffix(climate_entity, trv_index)
        self._attr_name = f"{climate_entity.name} {trv_suffix.replace('_', ' ').title()} Heating"
        self._attr_unique_id = f"{climate_entity.unique_id}_{trv_suffix}_heating"
        self._attr_icon = "mdi:fire"
        self._attr_device_class = "heat"

    @property
    def is_on(self):
        """Return true if this TRV is heating."""
        valve_entity = self._climate_entity._valve_entities[self._trv_index]
        return self._climate_entity._valve_positions.get(valve_entity, 0) > 0

    async def async_update(self):
        """Update the sensor."""
        pass