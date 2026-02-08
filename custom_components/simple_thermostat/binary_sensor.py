"""Binary sensor platform for Simple Thermostat."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Simple Thermostat binary sensor platform."""
    if discovery_info is None:
        return

    sensors = discovery_info.get("sensors", [])
    binary_sensors = [s for s in sensors if isinstance(s, BinarySensorEntity)]

    if binary_sensors:
        async_add_entities(binary_sensors, update_before_add=True)
