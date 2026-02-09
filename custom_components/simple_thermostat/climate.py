"""Climate platform for Simple Thermostat."""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .sensor import async_create_sensors
from .preset_manager import PresetManager

_LOGGER = logging.getLogger(__name__)

CONF_TEMP_SENSOR = "temperature_sensor"
CONF_TEMP_SENSOR_ID = "temperature_sensor_id"
CONF_VALVE_ENTITIES = "valve_entities"
CONF_CLIMATE_ENTITIES = "climate_entities"
CONF_TRV_IDS = "trv_ids"
CONF_AWAY_TEMP = "away_temp"
CONF_PRESENT_TEMP = "present_temp"
CONF_COSY_TEMP = "cosy_temp"
CONF_BINARY_THRESHOLD = "binary_threshold"
CONF_HYSTERESIS = "hysteresis"
CONF_SYNC_REMOTE_TEMP = "sync_remote_temp"
CONF_INITIAL_PRESET = "initial_preset"
CONF_SCHEDULE = "schedule"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_WINDOW_SENSOR = "window_sensor"
CONF_OUTDOOR_TEMP_SENSOR = "outdoor_temp_sensor"
CONF_GLOBAL_AWAY_SENSOR = "global_away_sensor"
CONF_PRESENCE_AWAY_DELAY = "presence_away_delay"
CONF_OUTDOOR_TEMP_THRESHOLD = "outdoor_temp_threshold"

DEFAULT_NAME = "Simple Thermostat"
DEFAULT_BINARY_THRESHOLD = 0.5
DEFAULT_HYSTERESIS = 0.3
DEFAULT_SYNC_REMOTE_TEMP = True
DEFAULT_INITIAL_PRESET = "present"
DEFAULT_PRESENCE_AWAY_DELAY = 15
DEFAULT_OUTDOOR_TEMP_THRESHOLD = 20.0

PRESET_AWAY = "away"
PRESET_PRESENT = "present"
PRESET_COSY = "cosy"
PRESET_OFF = "off"

CONTROL_MODE_BINARY_HEAT = "binary_heat"
CONTROL_MODE_BINARY_COOL = "binary_cool"
CONTROL_MODE_PROPORTIONAL = "proportional"
CONTROL_MODE_OFF = "off"

REMOTE_TEMP_SYNC_INTERVAL = timedelta(minutes=25)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Exclusive(CONF_TEMP_SENSOR_ID, "temp_sensor_config"): cv.string,
        vol.Exclusive(CONF_TEMP_SENSOR, "temp_sensor_config"): cv.entity_id,
        vol.Exclusive(CONF_TRV_IDS, "trv_config"): vol.All(
            cv.ensure_list,
            [
                vol.Any(
                    cv.string,  # Backward compatibility: simple string
                    vol.Schema({
                        vol.Required("id"): cv.string,
                        vol.Optional("name"): cv.string,
                    })
                )
            ]
        ),
        vol.Exclusive(CONF_VALVE_ENTITIES, "trv_config"): cv.entity_ids,
        vol.Optional(CONF_CLIMATE_ENTITIES): cv.entity_ids,
        vol.Required(CONF_AWAY_TEMP): vol.Coerce(float),
        vol.Required(CONF_PRESENT_TEMP): vol.Coerce(float),
        vol.Required(CONF_COSY_TEMP): vol.Coerce(float),
        vol.Optional(CONF_BINARY_THRESHOLD, default=DEFAULT_BINARY_THRESHOLD): vol.Coerce(
            float
        ),
        vol.Optional(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): vol.Coerce(float),
        vol.Optional(CONF_SYNC_REMOTE_TEMP, default=DEFAULT_SYNC_REMOTE_TEMP): cv.boolean,
        vol.Optional(CONF_INITIAL_PRESET, default=DEFAULT_INITIAL_PRESET): vol.In(
            [PRESET_AWAY, PRESET_PRESENT, PRESET_COSY, PRESET_OFF]
        ),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        # Schedule configuration
        vol.Optional(CONF_SCHEDULE): vol.Schema({
            vol.Optional("weekday"): [
                vol.Schema({
                    vol.Required("time"): cv.string,
                    vol.Required("preset"): vol.In([PRESET_AWAY, PRESET_PRESENT, PRESET_COSY, PRESET_OFF]),
                })
            ],
            vol.Optional("weekend"): [
                vol.Schema({
                    vol.Required("time"): cv.string,
                    vol.Required("preset"): vol.In([PRESET_AWAY, PRESET_PRESENT, PRESET_COSY, PRESET_OFF]),
                })
            ],
        }),
        # Override sensors
        vol.Optional(CONF_PRESENCE_SENSOR): cv.entity_id,
        vol.Optional(CONF_WINDOW_SENSOR): cv.entity_id,
        vol.Optional(CONF_OUTDOOR_TEMP_SENSOR): cv.entity_id,
        vol.Optional(CONF_GLOBAL_AWAY_SENSOR): cv.entity_id,
        # Tuning parameters
        vol.Optional(CONF_PRESENCE_AWAY_DELAY, default=DEFAULT_PRESENCE_AWAY_DELAY): vol.Coerce(int),
        vol.Optional(CONF_OUTDOOR_TEMP_THRESHOLD, default=DEFAULT_OUTDOOR_TEMP_THRESHOLD): vol.Coerce(float),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Simple Thermostat platform."""
    name = config.get(CONF_NAME)

    # Support simplified temperature_sensor_id configuration
    temp_sensor_id = config.get(CONF_TEMP_SENSOR_ID)
    if temp_sensor_id:
        # Auto-construct temperature sensor entity ID
        temp_sensor = f"sensor.{temp_sensor_id}_temperature"
        _LOGGER.info(f"Auto-constructed temperature sensor from temp_sensor_id: {temp_sensor}")
    else:
        # Use explicit temperature_sensor
        temp_sensor = config.get(CONF_TEMP_SENSOR)

    # Support simplified trv_ids configuration
    trv_ids_config = config.get(CONF_TRV_IDS)
    trv_names = []
    if trv_ids_config:
        # Parse TRV config (supports both string and dict format)
        trv_ids = []
        for trv_config in trv_ids_config:
            if isinstance(trv_config, str):
                # Backward compatibility: simple string
                trv_ids.append(trv_config)
                trv_names.append(None)
            elif isinstance(trv_config, dict):
                # New format: {id: "...", name: "..."}
                trv_ids.append(trv_config["id"])
                trv_names.append(trv_config.get("name"))

        # Auto-construct valve and climate entities from TRV IDs
        valve_entities = [f"number.{trv_id}_pi_heating_demand" for trv_id in trv_ids]
        climate_entities = [f"climate.{trv_id}" for trv_id in trv_ids]
        _LOGGER.info(f"Auto-constructed entities from trv_ids: valves={valve_entities}, climates={climate_entities}, names={trv_names}")
    else:
        # Use explicit valve_entities and climate_entities
        valve_entities = config.get(CONF_VALVE_ENTITIES)
        climate_entities = config.get(CONF_CLIMATE_ENTITIES)
        trv_ids = []

    away_temp = config.get(CONF_AWAY_TEMP)
    present_temp = config.get(CONF_PRESENT_TEMP)
    cosy_temp = config.get(CONF_COSY_TEMP)
    binary_threshold = config.get(CONF_BINARY_THRESHOLD)
    hysteresis = config.get(CONF_HYSTERESIS)
    sync_remote_temp = config.get(CONF_SYNC_REMOTE_TEMP)
    initial_preset = config.get(CONF_INITIAL_PRESET)
    unique_id = config.get(CONF_UNIQUE_ID)

    # Schedule and override sensors (optional)
    schedule_config = config.get(CONF_SCHEDULE)
    presence_sensor = config.get(CONF_PRESENCE_SENSOR)
    window_sensor = config.get(CONF_WINDOW_SENSOR)
    outdoor_temp_sensor = config.get(CONF_OUTDOOR_TEMP_SENSOR)
    global_away_sensor = config.get(CONF_GLOBAL_AWAY_SENSOR)
    presence_away_delay = config.get(CONF_PRESENCE_AWAY_DELAY)
    outdoor_temp_threshold = config.get(CONF_OUTDOOR_TEMP_THRESHOLD)

    thermostat = SimpleThermostat(
        hass,
        name,
        temp_sensor,
        valve_entities,
        climate_entities,
        away_temp,
        present_temp,
        cosy_temp,
        binary_threshold,
        hysteresis,
        sync_remote_temp,
        initial_preset,
        unique_id,
        trv_names,
        schedule_config,
        presence_sensor,
        window_sensor,
        outdoor_temp_sensor,
        global_away_sensor,
        presence_away_delay,
        outdoor_temp_threshold,
    )

    async_add_entities([thermostat])

    # Create diagnostic sensors
    sensors = await async_create_sensors(hass, thermostat)
    if sensors:
        # Load sensor platforms (non-blocking)
        hass.async_create_task(
            async_load_platform(
                hass,
                "sensor",
                "simple_thermostat",
                {"sensors": sensors},
                config
            )
        )
        hass.async_create_task(
            async_load_platform(
                hass,
                "binary_sensor",
                "simple_thermostat",
                {"sensors": sensors},
                config
            )
        )


class SimpleThermostat(ClimateEntity, RestoreEntity):
    """Simple Thermostat with hybrid control strategy."""

    def __init__(
        self,
        hass,
        name,
        temp_sensor,
        valve_entities,
        climate_entities,
        away_temp,
        present_temp,
        cosy_temp,
        binary_threshold,
        hysteresis,
        sync_remote_temp,
        initial_preset,
        unique_id,
        trv_names=None,
        schedule_config=None,
        presence_sensor=None,
        window_sensor=None,
        outdoor_temp_sensor=None,
        global_away_sensor=None,
        presence_away_delay=DEFAULT_PRESENCE_AWAY_DELAY,
        outdoor_temp_threshold=DEFAULT_OUTDOOR_TEMP_THRESHOLD,
    ):
        """Initialize the thermostat."""
        self.hass = hass
        self._attr_name = f"ST {name}"
        self._attr_unique_id = unique_id
        self._temp_sensor = temp_sensor
        self._valve_entities = valve_entities
        self._climate_entities = climate_entities
        self._trv_names = trv_names or []
        self._away_temp = away_temp
        self._present_temp = present_temp
        self._cosy_temp = cosy_temp
        self._binary_threshold = binary_threshold
        self._hysteresis = hysteresis
        self._sync_remote_temp = sync_remote_temp
        self._initial_preset = initial_preset

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_preset_modes = [PRESET_AWAY, PRESET_PRESENT, PRESET_COSY, PRESET_OFF]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )

        self._hvac_mode = HVACMode.OFF
        self._preset_mode = initial_preset
        self._cur_temp = None
        self._target_temp = present_temp
        self._enabled = False

        # Control state tracking
        self.control_mode = CONTROL_MODE_OFF
        self._valve_positions = {}  # entity_id -> position
        self._trv_internal_temps = {}  # trv_index -> temp

        # Initialize PresetManager
        self._preset_manager = PresetManager(
            hass,
            name,
            schedule_config,
            presence_sensor,
            window_sensor,
            outdoor_temp_sensor,
            global_away_sensor,
            presence_away_delay,
            outdoor_temp_threshold,
            initial_preset,
        )
        self._trv_target_temps = {}  # trv_index -> temp
        self._last_control_mode = None

        # Action history for logs (keep last 20 actions)
        self._action_history = []
        self._max_history = 20

        # Track state change listeners
        self._remove_listeners = []

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Set up PresetManager
        await self._preset_manager.async_setup()

        # Restore previous state
        last_state = await self.async_get_last_state()
        if last_state:
            self._hvac_mode = last_state.state
            if last_state.attributes.get("preset_mode"):
                # Check if it was a manual preset change
                self._preset_mode = last_state.attributes["preset_mode"]
                self._preset_manager.set_manual_preset(self._preset_mode)
            if last_state.attributes.get("temperature"):
                self._target_temp = last_state.attributes["temperature"]

        # Update preset from PresetManager
        self._preset_mode = self._preset_manager.get_active_preset()
        self._update_target_temp_from_preset()

        # Listen to temperature sensor changes
        self._remove_listeners.append(
            async_track_state_change_event(
                self.hass, [self._temp_sensor], self._async_temp_sensor_changed
            )
        )

        # Listen to TRV state changes (for reading internal temps)
        self._remove_listeners.append(
            async_track_state_change_event(
                self.hass, self._climate_entities, self._async_trv_state_changed
            )
        )

        # Update preset every minute (check for schedule changes)
        self._remove_listeners.append(
            async_track_time_interval(
                self.hass, self._async_update_preset, timedelta(minutes=1)
            )
        )

        # Refresh sensors every 15 seconds
        self._remove_listeners.append(
            async_track_time_interval(
                self.hass, self._async_refresh_sensors, timedelta(seconds=15)
            )
        )

        # Initialize TRVs on startup
        @callback
        def _async_startup(_):
            self.hass.async_create_task(self._async_initialize_trvs())

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

        # Schedule remote temperature sync if enabled
        if self._sync_remote_temp:
            self._remove_listeners.append(
                async_track_time_interval(
                    self.hass,
                    self._async_sync_remote_temperature,
                    REMOTE_TEMP_SYNC_INTERVAL,
                )
            )

        # Initial temperature read
        await self._async_update_temp()

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed."""
        # Clean up PresetManager listeners
        await self._preset_manager.async_cleanup()

        # Clean up local listeners
        for remove_listener in self._remove_listeners:
            remove_listener()
        self._remove_listeners.clear()

    @property
    def hvac_mode(self):
        """Return current HVAC mode."""
        return self._hvac_mode

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._cur_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def preset_mode(self):
        """Return the current preset mode."""
        return self._preset_mode

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        override_status = self._preset_manager.get_override_status()
        return {
            "control_mode": self.control_mode,
            "temperature_sensor": self._temp_sensor,  # For chart to find the room temp sensor
            "temperature_error": round(self._target_temp - self._cur_temp, 2) if self._cur_temp and self._target_temp else None,
            "valve_positions": self._valve_positions,
            "trv_internal_temps": self._trv_internal_temps,
            "trv_target_temps": self._trv_target_temps,
            "action_history": self._action_history[-10:],  # Last 10 actions for card
            # Preset temperatures for UI sliders
            "away_temp": self._away_temp,
            "present_temp": self._present_temp,
            "cosy_temp": self._cosy_temp,
            # Override status for UI
            "scheduled_preset": override_status["scheduled_preset"],
            "manual_override": override_status["manual_override"],
            "presence_override": override_status["presence_override"],
            "window_open": override_status["window_open"],
            "outdoor_temp_high": override_status["outdoor_temp_high"],
            "global_away": override_status["global_away"],
            # Schedule data for visualization
            "schedule": self._preset_manager._schedule_config if self._preset_manager._schedule_config else None,
        }

    def _log_action(self, message):
        """Log an action to history."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        action = {
            "time": timestamp,
            "message": message
        }

        self._action_history.append(action)

        # Keep only last N actions
        if len(self._action_history) > self._max_history:
            self._action_history = self._action_history[-self._max_history:]

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            self._hvac_mode = HVACMode.HEAT
            self._enabled = True

            # If preset was OFF, restore to PRESENT
            if self._preset_mode == PRESET_OFF:
                _LOGGER.info("%s: HVAC mode set to HEAT - restoring PRESENT preset", self.name)
                self._preset_mode = PRESET_PRESENT
                self._update_target_temp_from_preset()
                self._preset_manager.set_manual_preset(PRESET_PRESENT)

            self._log_action(f"HVAC mode set to HEAT (target: {self._target_temp}°C)")
            await self._async_control_heating()
        elif hvac_mode == HVACMode.OFF:
            _LOGGER.info("%s: HVAC mode set to OFF - forcing valves to 0%% and setting preset to OFF", self.name)
            self._hvac_mode = HVACMode.OFF
            self._enabled = False
            self.control_mode = CONTROL_MODE_OFF

            # Sync preset to OFF
            self._preset_mode = PRESET_OFF
            self._update_target_temp_from_preset()
            self._preset_manager.set_manual_preset(PRESET_OFF)

            # Force all valves to 0%
            await self._async_turn_off_all()
            self._log_action(f"HVAC mode set to OFF - heating disabled")

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._target_temp = temperature
        self._preset_mode = None  # Clear preset when manually setting temp
        self._log_action(f"Target temperature set to {temperature}°C (manual)")

        if self._hvac_mode == HVACMode.HEAT:
            await self._async_control_heating()

        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        if preset_mode not in self._attr_preset_modes:
            _LOGGER.warning("Invalid preset mode: %s", preset_mode)
            return

        # Notify PresetManager of manual change
        self._preset_manager.set_manual_preset(preset_mode)

        # Update local state
        self._preset_mode = preset_mode
        self._update_target_temp_from_preset()

        # Synchronize HVAC mode with preset
        if preset_mode == PRESET_OFF:
            # Preset OFF → Turn off HVAC completely
            _LOGGER.info("%s: Preset OFF - turning off HVAC mode and forcing valves to 0%%", self.name)
            self._hvac_mode = HVACMode.OFF
            self._enabled = False
            self.control_mode = CONTROL_MODE_OFF
            await self._async_turn_off_all()
            self._log_action(f"Preset OFF - heating disabled")
        else:
            # Preset AWAY/PRESENT/COSY → Ensure HVAC is HEAT
            if self._hvac_mode == HVACMode.OFF:
                _LOGGER.info("%s: Preset %s - automatically enabling HVAC mode HEAT", self.name, preset_mode)
                self._hvac_mode = HVACMode.HEAT
                self._enabled = True
                self._log_action(f"Preset {preset_mode.upper()} - HVAC enabled ({self._target_temp}°C)")
            else:
                self._log_action(f"Preset changed to {preset_mode.upper()} ({self._target_temp}°C)")

            # Run control logic
            await self._async_control_heating()

        self.async_write_ha_state()

    def _update_target_temp_from_preset(self):
        """Update target temperature based on current preset."""
        if self._preset_mode == PRESET_AWAY:
            self._target_temp = self._away_temp
        elif self._preset_mode == PRESET_PRESENT:
            self._target_temp = self._present_temp
        elif self._preset_mode == PRESET_COSY:
            self._target_temp = self._cosy_temp
        elif self._preset_mode == PRESET_OFF:
            self._target_temp = 5.0

    async def _async_temp_sensor_changed(self, event):
        """Handle temperature sensor changes."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.warning("%s: Temperature sensor unavailable or unknown", self.name)
            return

        old_temp = self._cur_temp
        await self._async_update_temp()

        _LOGGER.info(
            "%s: Temperature changed: %.1f°C -> %.1f°C (target: %.1f°C, error: %.1f°C)",
            self.name,
            old_temp if old_temp else 0,
            self._cur_temp if self._cur_temp else 0,
            self._target_temp if self._target_temp else 0,
            (self._target_temp - self._cur_temp) if (self._target_temp and self._cur_temp) else 0
        )

        if self._hvac_mode == HVACMode.HEAT:
            await self._async_control_heating()
        else:
            _LOGGER.info("%s: Skipping control heating - HVAC mode is %s", self.name, self._hvac_mode)

        self.async_write_ha_state()

    async def _async_trv_state_changed(self, event):
        """Handle TRV state changes (to read internal temps)."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        entity_id = new_state.entity_id
        if entity_id in self._climate_entities:
            idx = self._climate_entities.index(entity_id)
            internal_temp = new_state.attributes.get("current_temperature")
            if internal_temp is not None:
                self._trv_internal_temps[idx] = float(internal_temp)

        self.async_write_ha_state()

    async def _async_refresh_sensors(self, _):
        """Refresh all sensor readings every 15 seconds."""
        await self._async_read_valve_positions()
        await self._async_read_trv_temps()

        # Safety check: If HVAC is OFF but any valve is open, force them closed
        if self._hvac_mode == HVACMode.OFF:
            any_valve_open = any(pos > 0 for pos in self._valve_positions.values())
            if any_valve_open:
                _LOGGER.warning(
                    "%s: SAFETY CHECK - HVAC is OFF but valves are open. Forcing to 0%%",
                    self.name
                )
                await self._async_turn_off_all()

        self.async_write_ha_state()

    async def _async_read_trv_temps(self):
        """Read TRV internal and target temperatures."""
        for idx, climate_entity in enumerate(self._climate_entities):
            climate_state = self.hass.states.get(climate_entity)
            if climate_state and climate_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                internal_temp = climate_state.attributes.get("current_temperature")
                target_temp = climate_state.attributes.get("temperature")

                if internal_temp is not None:
                    self._trv_internal_temps[idx] = float(internal_temp)
                if target_temp is not None:
                    self._trv_target_temps[idx] = float(target_temp)

    async def _async_update_preset(self, _):
        """Update preset from PresetManager."""
        new_preset = self._preset_manager.get_active_preset()

        if new_preset != self._preset_mode:
            _LOGGER.info(
                "%s: Preset automatically changed: %s → %s",
                self.name,
                self._preset_mode,
                new_preset
            )
            self._preset_mode = new_preset
            self._update_target_temp_from_preset()
            self._log_action(f"Preset auto-changed to {new_preset.upper()} ({self._target_temp}°C)")

            if self._hvac_mode == HVACMode.HEAT:
                await self._async_control_heating()

            self.async_write_ha_state()

    async def _async_update_temp(self):
        """Update current temperature from sensor."""
        sensor_state = self.hass.states.get(self._temp_sensor)
        if sensor_state and sensor_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._cur_temp = float(sensor_state.state)
            except ValueError:
                _LOGGER.warning("Unable to parse temperature: %s", sensor_state.state)

    async def _async_initialize_trvs(self):
        """Initialize TRVs: set to 30°C and manual mode."""
        _LOGGER.info("%s: Initializing TRVs", self.name)

        for climate_entity in self._climate_entities:
            # Set target temperature to 30°C (max)
            try:
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {ATTR_ENTITY_ID: climate_entity, ATTR_TEMPERATURE: 30},
                    blocking=True,
                )
                _LOGGER.info("%s: Set %s to 30°C", self.name, climate_entity)
            except Exception as err:
                _LOGGER.error(
                    "%s: Failed to set temperature for %s: %s",
                    self.name,
                    climate_entity,
                    err,
                )

            # Set operating mode to manual (Bosch-specific)
            try:
                # Extract friendly name from entity_id for MQTT topic
                # This assumes Zigbee2MQTT naming convention
                friendly_name = climate_entity.replace("climate.", "").replace("_", " ")
                await self.hass.services.async_call(
                    "mqtt",
                    "publish",
                    {
                        "topic": f"zigbee2mqtt/{friendly_name}/set",
                        "payload": '{"operating_mode": "manual"}',
                    },
                    blocking=False,
                )
                _LOGGER.info(
                    "%s: Set %s to manual mode", self.name, climate_entity
                )
            except Exception as err:
                _LOGGER.warning(
                    "%s: Could not set manual mode for %s (may not be supported): %s",
                    self.name,
                    climate_entity,
                    err,
                )

        # Read initial TRV temperatures
        for idx, climate_entity in enumerate(self._climate_entities):
            trv_state = self.hass.states.get(climate_entity)
            if trv_state:
                internal_temp = trv_state.attributes.get("current_temperature")
                if internal_temp is not None:
                    self._trv_internal_temps[idx] = float(internal_temp)

    async def _async_control_heating(self):
        """Main control logic: hybrid binary + proportional control."""
        _LOGGER.info(
            "%s: _async_control_heating called - enabled=%s, cur_temp=%s, target_temp=%s",
            self.name,
            self._enabled,
            self._cur_temp,
            self._target_temp
        )

        if not self._enabled or self._cur_temp is None or self._target_temp is None:
            _LOGGER.info("%s: Skipping control - not enabled or temps None", self.name)
            return

        error = self._target_temp - self._cur_temp

        _LOGGER.info(
            "%s: Control logic - error=%.2f°C, binary_threshold=%.2f°C",
            self.name,
            error,
            self._binary_threshold
        )

        # Determine control mode based on error
        if error > self._binary_threshold:
            # Too cold - binary heating mode
            _LOGGER.info("%s: Error > threshold → binary heat mode", self.name)
            await self._async_set_binary_heat_mode()
        elif error < -self._binary_threshold:
            # Too hot - binary cooling mode (turn off)
            _LOGGER.info("%s: Error < -threshold → binary cool mode (turn off)", self.name)
            await self._async_set_binary_cool_mode()
        else:
            # Near target - proportional control mode
            _LOGGER.info("%s: Error within threshold → proportional mode", self.name)
            await self._async_set_proportional_mode()

        # Log mode changes
        if self.control_mode != self._last_control_mode:
            _LOGGER.info(
                "%s: Control mode changed: %s -> %s (error: %.2f°C)",
                self.name,
                self._last_control_mode,
                self.control_mode,
                error,
            )
            self._log_action(
                f"Mode: {self.control_mode.replace('_', ' ').title()} (error: {error:.2f}°C)"
            )
            self._last_control_mode = self.control_mode

    async def _async_set_binary_heat_mode(self):
        """Binary heating: valve 100%, temp 30°C."""
        self.control_mode = CONTROL_MODE_BINARY_HEAT

        # Set all valves to 100%
        for valve_entity in self._valve_entities:
            await self._async_set_valve_position(valve_entity, 100)

        # Set all TRVs to max temperature (30°C)
        for idx, climate_entity in enumerate(self._climate_entities):
            await self._async_set_trv_temperature(climate_entity, idx, 30)

        # Read back actual valve positions for monitoring
        await self._async_read_valve_positions()

    async def _async_set_binary_cool_mode(self):
        """Binary cooling: valve 0%, temp 5°C."""
        self.control_mode = CONTROL_MODE_BINARY_COOL

        # Set all valves to 0%
        for valve_entity in self._valve_entities:
            await self._async_set_valve_position(valve_entity, 0)

        # Set all TRVs to min temperature (5°C)
        for idx, climate_entity in enumerate(self._climate_entities):
            await self._async_set_trv_temperature(climate_entity, idx, 5)

        # Read back actual valve positions for monitoring
        await self._async_read_valve_positions()

    async def _async_set_proportional_mode(self):
        """Proportional control: calculate TRV target from external sensor."""
        self.control_mode = CONTROL_MODE_PROPORTIONAL

        # For each TRV, calculate target temperature
        for idx, climate_entity in enumerate(self._climate_entities):
            trv_internal_temp = self._trv_internal_temps.get(idx)

            if trv_internal_temp is None:
                _LOGGER.warning(
                    "%s: No internal temp for TRV %d, skipping proportional control",
                    self.name,
                    idx + 1,
                )
                continue

            # Calculate TRV target: (room_target - external_temp) + trv_internal
            calculated_target = (
                self._target_temp - self._cur_temp
            ) + trv_internal_temp

            # Clamp to valid range (5-30°C)
            calculated_target = max(5.0, min(30.0, calculated_target))

            await self._async_set_trv_temperature(
                climate_entity, idx, calculated_target
            )

        # In proportional mode, we don't directly control valve position
        # The TRV controls it based on the target temperature we set
        # But we should read back the valve positions for status
        await self._async_read_valve_positions()

    async def _async_read_valve_positions(self):
        """Read current valve positions from all valve entities."""
        for valve_entity in self._valve_entities:
            valve_state = self.hass.states.get(valve_entity)
            if valve_state and valve_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                try:
                    self._valve_positions[valve_entity] = float(valve_state.state)
                    _LOGGER.info(
                        "%s: Read valve position from %s = %s%%",
                        self.name,
                        valve_entity,
                        valve_state.state
                    )
                except ValueError:
                    pass

    async def _async_turn_off_all(self):
        """Turn off all heating."""
        # Set all valves to 0%
        for valve_entity in self._valve_entities:
            await self._async_set_valve_position(valve_entity, 0)

        # Set all TRVs to min temperature
        for idx, climate_entity in enumerate(self._climate_entities):
            await self._async_set_trv_temperature(climate_entity, idx, 5)

    async def _async_set_valve_position(self, valve_entity, position):
        """Set valve position (0-100)."""
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {ATTR_ENTITY_ID: valve_entity, "value": position},
                blocking=True,
            )
            self._valve_positions[valve_entity] = position
            _LOGGER.debug(
                "%s: Set valve %s to %d%%", self.name, valve_entity, position
            )
        except Exception as err:
            _LOGGER.error(
                "%s: Failed to set valve %s to %d%%: %s",
                self.name,
                valve_entity,
                position,
                err,
            )

    async def _async_set_trv_temperature(self, climate_entity, trv_index, temperature):
        """Set TRV target temperature."""
        try:
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {ATTR_ENTITY_ID: climate_entity, ATTR_TEMPERATURE: temperature},
                blocking=True,
            )
            self._trv_target_temps[trv_index] = temperature
            _LOGGER.debug(
                "%s: Set TRV %s to %.1f°C",
                self.name,
                climate_entity,
                temperature,
            )
        except Exception as err:
            _LOGGER.error(
                "%s: Failed to set TRV %s to %.1f°C: %s",
                self.name,
                climate_entity,
                temperature,
                err,
            )

    async def _async_sync_remote_temperature(self, now=None):
        """Send external temperature to TRVs via MQTT."""
        if self._cur_temp is None:
            return

        for climate_entity in self._climate_entities:
            try:
                # Extract friendly name from entity_id
                friendly_name = climate_entity.replace("climate.", "").replace("_", " ")
                await self.hass.services.async_call(
                    "mqtt",
                    "publish",
                    {
                        "topic": f"zigbee2mqtt/{friendly_name}/set",
                        "payload": f'{{"remote_temperature": {self._cur_temp}}}',
                    },
                    blocking=False,
                )
                _LOGGER.debug(
                    "%s: Synced remote temperature %.1f°C to %s",
                    self.name,
                    self._cur_temp,
                    climate_entity,
                )
            except Exception as err:
                _LOGGER.warning(
                    "%s: Failed to sync remote temperature to %s: %s",
                    self.name,
                    climate_entity,
                    err,
                )