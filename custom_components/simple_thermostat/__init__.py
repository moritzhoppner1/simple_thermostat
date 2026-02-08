"""Simple Thermostat integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "simple_thermostat"


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

    return True
