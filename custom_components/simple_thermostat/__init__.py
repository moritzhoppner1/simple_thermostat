"""Simple Thermostat integration for Home Assistant."""
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "simple_thermostat"


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Simple Thermostat component."""

    # Register the custom Lovelace card
    card_path = Path(__file__).parent / "www" / "simple-thermostat-card.js"

    if card_path.exists():
        # Register as a Lovelace resource
        hass.http.register_static_path(
            f"/simple_thermostat/simple-thermostat-card.js",
            str(card_path),
            cache_headers=False
        )

        _LOGGER.info(
            "Registered Simple Thermostat card at /simple_thermostat/simple-thermostat-card.js"
        )
        _LOGGER.info(
            "Add this to your Lovelace resources: "
            "url: /simple_thermostat/simple-thermostat-card.js, type: module"
        )
    else:
        _LOGGER.warning(
            "Simple Thermostat card file not found at %s", card_path
        )

    return True
