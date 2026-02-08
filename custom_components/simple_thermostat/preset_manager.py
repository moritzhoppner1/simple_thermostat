"""Preset Manager - Handles scheduling and override logic for Simple Thermostat."""
from datetime import datetime, timedelta
import logging
from typing import Optional

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

_LOGGER = logging.getLogger(__name__)

# Priority order (highest to lowest)
PRIORITY_WINDOW = 1
PRIORITY_OUTDOOR_TEMP = 2
PRIORITY_MANUAL = 3
PRIORITY_PRESENCE = 4
PRIORITY_GLOBAL_AWAY = 5
PRIORITY_SCHEDULE = 6


class PresetManager:
    """Manages preset scheduling and overrides with priority logic.

    Priority Order (highest to lowest):
    1. Window open → OFF
    2. Outdoor temp >threshold → OFF
    3. Manual user change
    4. Presence in room → PRESENT (only overrides AWAY)
    5. Global away sensor → AWAY
    6. Schedule (weekday/weekend)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        schedule_config: Optional[dict],
        presence_sensor: Optional[str],
        window_sensor: Optional[str],
        outdoor_temp_sensor: Optional[str],
        global_away_sensor: Optional[str],
        presence_away_delay: int = 15,
        outdoor_temp_threshold: float = 20.0,
        initial_preset: str = "present",
    ):
        """Initialize PresetManager."""
        self.hass = hass
        self.name = name
        self._schedule_config = schedule_config
        self._presence_sensor = presence_sensor
        self._window_sensor = window_sensor
        self._outdoor_temp_sensor = outdoor_temp_sensor
        self._global_away_sensor = global_away_sensor
        self._presence_away_delay = presence_away_delay
        self._outdoor_temp_threshold = outdoor_temp_threshold
        self._initial_preset = initial_preset

        # State tracking
        self._scheduled_preset: Optional[str] = None
        self._manual_override_preset: Optional[str] = None
        self._presence_override_active: bool = False
        self._last_presence_clear_time: Optional[datetime] = None
        self._window_open: bool = False
        self._outdoor_temp_high: bool = False
        self._global_away_active: bool = False

        # Parse schedule
        self._weekday_schedule = self._parse_schedule(
            schedule_config.get("weekday", []) if schedule_config else []
        )
        self._weekend_schedule = self._parse_schedule(
            schedule_config.get("weekend", []) if schedule_config else []
        )

        # Track state change listeners (for cleanup)
        self._listeners = []

    async def async_setup(self):
        """Set up listeners and initial state."""
        # Listen to sensor state changes
        if self._presence_sensor:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass, [self._presence_sensor], self._async_presence_changed
                )
            )
            await self._update_presence_state()

        if self._window_sensor:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass, [self._window_sensor], self._async_window_changed
                )
            )
            await self._update_window_state()

        if self._outdoor_temp_sensor:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass,
                    [self._outdoor_temp_sensor],
                    self._async_outdoor_temp_changed,
                )
            )
            await self._update_outdoor_temp_state()

        if self._global_away_sensor:
            self._listeners.append(
                async_track_state_change_event(
                    self.hass, [self._global_away_sensor], self._async_global_away_changed
                )
            )
            await self._update_global_away_state()

        # Update scheduled preset every minute
        self._listeners.append(
            async_track_time_interval(
                self.hass, self._async_update_schedule, timedelta(minutes=1)
            )
        )
        await self._async_update_schedule(None)

    async def async_cleanup(self):
        """Clean up listeners."""
        for listener in self._listeners:
            listener()
        self._listeners.clear()

    def _parse_schedule(self, schedule_list: list) -> list:
        """Parse schedule config into sorted list of (time, preset) tuples."""
        parsed = []
        for entry in schedule_list:
            time_str = entry.get("time")
            preset = entry.get("preset")
            if time_str and preset:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    parsed.append((hour * 60 + minute, preset))  # Store as minutes since midnight
                except ValueError:
                    _LOGGER.error(
                        "%s: Invalid time format in schedule: %s", self.name, time_str
                    )
        return sorted(parsed)  # Sort by time

    def get_active_preset(self) -> str:
        """Get the current active preset after applying all overrides."""
        # Start with scheduled preset or initial preset
        base_preset = self._scheduled_preset or self._initial_preset

        # Apply overrides in reverse priority order (lowest to highest)
        active_preset = base_preset

        # 6. Schedule (already in base_preset)

        # 5. Global away
        if self._global_away_active:
            active_preset = "away"

        # 4. Presence (only overrides AWAY)
        if self._presence_override_active and active_preset == "away":
            active_preset = "present"

        # 3. Manual override
        if self._manual_override_preset is not None:
            active_preset = self._manual_override_preset

        # 2. Outdoor temperature
        if self._outdoor_temp_high:
            active_preset = "off"

        # 1. Window open
        if self._window_open:
            active_preset = "off"

        return active_preset

    def set_manual_preset(self, preset: str):
        """User manually changed preset."""
        _LOGGER.info("%s: Manual preset change: %s", self.name, preset)
        self._manual_override_preset = preset

    def clear_manual_override(self):
        """Clear manual override (called when schedule changes)."""
        if self._manual_override_preset is not None:
            _LOGGER.info("%s: Clearing manual override", self.name)
            self._manual_override_preset = None

    def get_override_status(self) -> dict:
        """Get current override status for UI display."""
        return {
            "scheduled_preset": self._scheduled_preset,
            "manual_override": self._manual_override_preset,
            "presence_override": self._presence_override_active,
            "window_open": self._window_open,
            "outdoor_temp_high": self._outdoor_temp_high,
            "global_away": self._global_away_active,
        }

    async def _async_update_schedule(self, _):
        """Update scheduled preset based on current time."""
        now = datetime.now()
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6

        schedule = self._weekend_schedule if is_weekend else self._weekday_schedule

        if not schedule:
            # No schedule configured, keep initial preset
            if self._scheduled_preset is None:
                self._scheduled_preset = self._initial_preset
            return

        # Find current scheduled preset
        current_minutes = now.hour * 60 + now.minute
        scheduled_preset = None

        for time_minutes, preset in schedule:
            if current_minutes >= time_minutes:
                scheduled_preset = preset
            else:
                break

        if scheduled_preset is None:
            # Before first scheduled time, use last preset from previous day
            scheduled_preset = schedule[-1][1]

        # Check if schedule changed
        if self._scheduled_preset != scheduled_preset:
            old_preset = self._scheduled_preset
            self._scheduled_preset = scheduled_preset
            _LOGGER.info(
                "%s: Schedule changed: %s → %s", self.name, old_preset, scheduled_preset
            )
            # Clear manual override when schedule changes
            self.clear_manual_override()

    @callback
    async def _async_presence_changed(self, event):
        """Handle presence sensor state change."""
        await self._update_presence_state()

    async def _update_presence_state(self):
        """Update presence override state."""
        if not self._presence_sensor:
            return

        state = self.hass.states.get(self._presence_sensor)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        presence_detected = state.state == STATE_ON

        if presence_detected:
            # Presence detected → activate override immediately
            if not self._presence_override_active:
                _LOGGER.info("%s: Presence detected → override to PRESENT", self.name)
                self._presence_override_active = True
            self._last_presence_clear_time = None
        else:
            # Presence cleared → start 15-minute timer
            if self._presence_override_active:
                if self._last_presence_clear_time is None:
                    self._last_presence_clear_time = datetime.now()
                    _LOGGER.info(
                        "%s: Presence cleared → waiting %d minutes",
                        self.name,
                        self._presence_away_delay,
                    )
                else:
                    # Check if delay has passed
                    elapsed = datetime.now() - self._last_presence_clear_time
                    if elapsed >= timedelta(minutes=self._presence_away_delay):
                        _LOGGER.info(
                            "%s: Presence delay expired → clearing override", self.name
                        )
                        self._presence_override_active = False
                        self._last_presence_clear_time = None

    @callback
    async def _async_window_changed(self, event):
        """Handle window sensor state change."""
        await self._update_window_state()

    async def _update_window_state(self):
        """Update window open state."""
        if not self._window_sensor:
            return

        state = self.hass.states.get(self._window_sensor)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        window_open = state.state == STATE_ON

        if window_open != self._window_open:
            self._window_open = window_open
            _LOGGER.info("%s: Window %s", self.name, "opened" if window_open else "closed")

            if not window_open:
                # Window closed → clear manual override and resume schedule
                self.clear_manual_override()

    @callback
    async def _async_outdoor_temp_changed(self, event):
        """Handle outdoor temperature sensor state change."""
        await self._update_outdoor_temp_state()

    async def _update_outdoor_temp_state(self):
        """Update outdoor temperature state."""
        if not self._outdoor_temp_sensor:
            return

        state = self.hass.states.get(self._outdoor_temp_sensor)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        try:
            temp = float(state.state)
            outdoor_temp_high = temp > self._outdoor_temp_threshold

            if outdoor_temp_high != self._outdoor_temp_high:
                self._outdoor_temp_high = outdoor_temp_high
                _LOGGER.info(
                    "%s: Outdoor temperature %s threshold (%.1f°C)",
                    self.name,
                    "above" if outdoor_temp_high else "below",
                    temp,
                )
        except ValueError:
            _LOGGER.warning(
                "%s: Invalid outdoor temperature value: %s", self.name, state.state
            )

    @callback
    async def _async_global_away_changed(self, event):
        """Handle global away sensor state change."""
        await self._update_global_away_state()

    async def _update_global_away_state(self):
        """Update global away state."""
        if not self._global_away_sensor:
            return

        state = self.hass.states.get(self._global_away_sensor)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        global_away = state.state == STATE_ON

        if global_away != self._global_away_active:
            self._global_away_active = global_away
            _LOGGER.info(
                "%s: Global away %s", self.name, "activated" if global_away else "deactivated"
            )
