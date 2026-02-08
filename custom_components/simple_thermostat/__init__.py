"""Simple Thermostat integration for Home Assistant."""
import logging
from pathlib import Path
import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "simple_thermostat"

SERVICE_SET_PRESET_TEMPERATURE = "set_preset_temperature"

SET_PRESET_TEMPERATURE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("away_temp"): vol.Coerce(float),
    vol.Optional("present_temp"): vol.Coerce(float),
    vol.Optional("cosy_temp"): vol.Coerce(float),
})


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Simple Thermostat component."""

    # Register the custom Lovelace card
    www_path = Path(__file__).parent / "www"

    if www_path.exists():
        # Register as a Lovelace resource
        await hass.http.async_register_static_paths([
            StaticPathConfig("/simple_thermostat", str(www_path), False)
        ])

        _LOGGER.info(
            "Registered Simple Thermostat card at /simple_thermostat/simple-thermostat-card.js"
        )
    else:
        _LOGGER.warning(
            "Simple Thermostat card www folder not found at %s", www_path
        )

    async def async_set_preset_temperature(call: ServiceCall):
        """Handle the set_preset_temperature service call."""
        entity_id = call.data.get("entity_id")

        # Get the climate entity
        climate_entity = None
        for component in hass.data.get("entity_components", {}).values():
            if hasattr(component, "entities"):
                for entity in component.entities:
                    if entity.entity_id == entity_id:
                        climate_entity = entity
                        break
            if climate_entity:
                break

        if not climate_entity:
            _LOGGER.error("Entity %s not found", entity_id)
            return

        # Update preset temperatures
        if "away_temp" in call.data:
            climate_entity._away_temp = call.data["away_temp"]
        if "present_temp" in call.data:
            climate_entity._present_temp = call.data["present_temp"]
        if "cosy_temp" in call.data:
            climate_entity._cosy_temp = call.data["cosy_temp"]

        # Update target temp if current preset was modified
        climate_entity._update_target_temp_from_preset()

        # Re-apply heating control with new temperature
        if climate_entity._hvac_mode == "heat":
            await climate_entity._async_control_heating()

        # Update state
        climate_entity.async_write_ha_state()

        _LOGGER.info(
            "%s: Preset temperatures updated - away: %s, present: %s, cosy: %s",
            climate_entity.name,
            climate_entity._away_temp,
            climate_entity._present_temp,
            climate_entity._cosy_temp,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PRESET_TEMPERATURE,
        async_set_preset_temperature,
        schema=SET_PRESET_TEMPERATURE_SCHEMA,
    )

    return True
