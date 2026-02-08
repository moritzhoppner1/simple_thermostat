"""Tests for PresetManager."""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from custom_components.simple_thermostat.preset_manager import PresetManager
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNAVAILABLE


class TestScheduleParsing:
    """Test schedule parsing and calculation."""

    def test_parse_valid_schedule(self, mock_hass, basic_schedule_config):
        """Test parsing a valid schedule configuration."""
        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )

        # Check weekday schedule
        assert len(manager._weekday_schedule) == 4
        assert manager._weekday_schedule[0] == (360, "present")  # 06:00
        assert manager._weekday_schedule[1] == (480, "away")  # 08:00
        assert manager._weekday_schedule[2] == (1020, "present")  # 17:00
        assert manager._weekday_schedule[3] == (1320, "cosy")  # 22:00

        # Check weekend schedule
        assert len(manager._weekend_schedule) == 2
        assert manager._weekend_schedule[0] == (480, "present")  # 08:00
        assert manager._weekend_schedule[1] == (1380, "cosy")  # 23:00

    def test_no_schedule_configured(self, mock_hass):
        """Test behavior when no schedule is configured."""
        manager = PresetManager(
            mock_hass, "Test", None, None, None, None, None, initial_preset="present"
        )

        assert manager._weekday_schedule == []
        assert manager._weekend_schedule == []
        assert manager.get_active_preset() == "present"


class TestScheduleCalculation:
    """Test scheduled preset calculation at different times."""

    @pytest.mark.asyncio
    async def test_weekday_morning(self, mock_hass, basic_schedule_config, mock_datetime):
        """Test weekday morning preset (06:00-08:00 = present)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 7, 0))  # Monday 07:00

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        assert manager._scheduled_preset == "present"
        assert manager.get_active_preset() == "present"

    @pytest.mark.asyncio
    async def test_weekday_work_hours(self, mock_hass, basic_schedule_config, mock_datetime):
        """Test weekday work hours (08:00-17:00 = away)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 12, 0))  # Monday 12:00

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        assert manager._scheduled_preset == "away"
        assert manager.get_active_preset() == "away"

    @pytest.mark.asyncio
    async def test_weekday_evening(self, mock_hass, basic_schedule_config, mock_datetime):
        """Test weekday evening (17:00-22:00 = present)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 30))  # Monday 19:30

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        assert manager._scheduled_preset == "present"
        assert manager.get_active_preset() == "present"

    @pytest.mark.asyncio
    async def test_weekday_night(self, mock_hass, basic_schedule_config, mock_datetime):
        """Test weekday night (22:00+ = cosy)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 23, 0))  # Monday 23:00

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        assert manager._scheduled_preset == "cosy"
        assert manager.get_active_preset() == "cosy"

    @pytest.mark.asyncio
    async def test_weekend_schedule(self, mock_hass, basic_schedule_config, mock_datetime):
        """Test weekend schedule (Saturday)."""
        mock_datetime.set_time(datetime(2024, 1, 20, 10, 0))  # Saturday 10:00

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        assert manager._scheduled_preset == "present"
        assert manager.get_active_preset() == "present"

    @pytest.mark.asyncio
    async def test_before_first_scheduled_time(
        self, mock_hass, basic_schedule_config, mock_datetime
    ):
        """Test time before first scheduled entry (use last preset from previous day)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 3, 0))  # Monday 03:00 AM

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        # Should use last preset from weekday schedule (22:00 = cosy)
        assert manager._scheduled_preset == "cosy"


class TestManualOverride:
    """Test manual preset override behavior."""

    @pytest.mark.asyncio
    async def test_manual_override_schedule(
        self, mock_hass, basic_schedule_config, mock_datetime
    ):
        """Test manual override takes precedence over schedule."""
        mock_datetime.set_time(datetime(2024, 1, 15, 12, 0))  # Monday 12:00 (away scheduled)

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        # Schedule says away
        assert manager._scheduled_preset == "away"

        # User manually changes to cosy
        manager.set_manual_preset("cosy")
        assert manager.get_active_preset() == "cosy"

    @pytest.mark.asyncio
    async def test_manual_override_cleared_on_schedule_change(
        self, mock_hass, basic_schedule_config, mock_datetime
    ):
        """Test manual override is cleared when schedule changes."""
        mock_datetime.set_time(datetime(2024, 1, 15, 12, 0))  # Monday 12:00

        manager = PresetManager(
            mock_hass, "Test", basic_schedule_config, None, None, None, None
        )
        await manager._async_update_schedule(None)

        # User manually changes preset
        manager.set_manual_preset("cosy")
        assert manager.get_active_preset() == "cosy"

        # Schedule changes at 17:00
        mock_datetime.set_time(datetime(2024, 1, 15, 17, 0))
        await manager._async_update_schedule(None)

        # Manual override should be cleared, now follows schedule
        assert manager._scheduled_preset == "present"
        assert manager.get_active_preset() == "present"


class TestPresenceOverride:
    """Test presence-based override behavior."""

    @pytest.mark.asyncio
    async def test_presence_overrides_away(self, mock_hass, mock_state, mock_datetime):
        """Test presence detection overrides AWAY preset."""
        mock_datetime.set_time(datetime(2024, 1, 15, 12, 0))

        schedule_config = {"weekday": [{"time": "08:00", "preset": "away"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.test_presence",
            None,
            None,
            None,
        )

        # Schedule says away
        await manager._async_update_schedule(None)
        assert manager._scheduled_preset == "away"

        # Simulate presence detected
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_presence", STATE_ON
        )
        await manager._update_presence_state()

        # Should override to present
        assert manager.get_active_preset() == "present"

    @pytest.mark.asyncio
    async def test_presence_does_not_override_present(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test presence does NOT override PRESENT or COSY."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.test_presence",
            None,
            None,
            None,
        )

        await manager._async_update_schedule(None)
        assert manager._scheduled_preset == "present"

        # Simulate presence detected
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_presence", STATE_ON
        )
        await manager._update_presence_state()

        # Should stay present (not boost to cosy)
        assert manager.get_active_preset() == "present"

    @pytest.mark.asyncio
    async def test_presence_15_minute_delay(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test 15-minute delay after presence clears."""
        from datetime import timedelta

        manager = PresetManager(
            mock_hass,
            "Test",
            None,
            "binary_sensor.test_presence",
            None,
            None,
            None,
            presence_away_delay=15,
            initial_preset="away",
        )

        # Presence detected
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_presence", STATE_ON
        )
        await manager._update_presence_state()
        assert manager._presence_override_active is True

        # Presence cleared
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_presence", STATE_OFF
        )
        await manager._update_presence_state()

        # Should still be active (within 15 minutes)
        assert manager._presence_override_active is True
        assert manager._last_presence_clear_time is not None

        # Simulate 15 minutes passing
        original_time = manager._last_presence_clear_time
        mock_datetime.set_time(original_time + timedelta(minutes=16))
        await manager._update_presence_state()

        # Should now be cleared
        assert manager._presence_override_active is False


class TestWindowOverride:
    """Test window open/close override behavior."""

    @pytest.mark.asyncio
    async def test_window_open_forces_off(self, mock_hass, mock_state):
        """Test window open immediately forces OFF."""
        manager = PresetManager(
            mock_hass,
            "Test",
            None,
            None,
            "binary_sensor.test_window",
            None,
            None,
            initial_preset="present",
        )

        # Window closed, normal operation
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_window", STATE_OFF
        )
        await manager._update_window_state()
        assert manager.get_active_preset() == "present"

        # Window opened
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_window", STATE_ON
        )
        await manager._update_window_state()

        # Should force OFF
        assert manager._window_open is True
        assert manager.get_active_preset() == "off"

    @pytest.mark.asyncio
    async def test_window_overrides_manual(self, mock_hass, mock_state):
        """Test window open overrides even manual preset."""
        manager = PresetManager(
            mock_hass,
            "Test",
            None,
            None,
            "binary_sensor.test_window",
            None,
            None,
            initial_preset="present",
        )

        # User manually sets to cosy
        manager.set_manual_preset("cosy")
        assert manager.get_active_preset() == "cosy"

        # Window opened
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_window", STATE_ON
        )
        await manager._update_window_state()

        # Window overrides manual
        assert manager.get_active_preset() == "off"

    @pytest.mark.asyncio
    async def test_window_close_clears_manual_override(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test window closing clears manual override and resumes schedule."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            None,
            "binary_sensor.test_window",
            None,
            None,
        )

        await manager._async_update_schedule(None)

        # User manually set to cosy
        manager.set_manual_preset("cosy")
        assert manager.get_active_preset() == "cosy"

        # Window opened then closed
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_window", STATE_ON
        )
        await manager._update_window_state()

        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.test_window", STATE_OFF
        )
        await manager._update_window_state()

        # Manual override cleared, should follow schedule
        assert manager._manual_override_preset is None
        assert manager.get_active_preset() == "present"


class TestOutdoorTemperature:
    """Test outdoor temperature override."""

    @pytest.mark.asyncio
    async def test_outdoor_temp_high_forces_off(self, mock_hass, mock_state):
        """Test outdoor temp >20°C forces OFF."""
        manager = PresetManager(
            mock_hass,
            "Test",
            None,
            None,
            None,
            "sensor.outdoor_temp",
            None,
            outdoor_temp_threshold=20.0,
            initial_preset="present",
        )

        # Outdoor temp below threshold
        mock_hass.states.get.return_value = mock_state("sensor.outdoor_temp", "18.5")
        await manager._update_outdoor_temp_state()
        assert manager.get_active_preset() == "present"

        # Outdoor temp above threshold
        mock_hass.states.get.return_value = mock_state("sensor.outdoor_temp", "22.0")
        await manager._update_outdoor_temp_state()

        # Should force OFF
        assert manager._outdoor_temp_high is True
        assert manager.get_active_preset() == "off"

    @pytest.mark.asyncio
    async def test_outdoor_temp_overrides_schedule(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test outdoor temp overrides schedule but not manual."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            None,
            None,
            "sensor.outdoor_temp",
            None,
            outdoor_temp_threshold=20.0,
        )

        await manager._async_update_schedule(None)

        # Outdoor temp high
        mock_hass.states.get.return_value = mock_state("sensor.outdoor_temp", "25.0")
        await manager._update_outdoor_temp_state()

        # Overrides schedule
        assert manager.get_active_preset() == "off"


class TestGlobalAway:
    """Test global away sensor."""

    @pytest.mark.asyncio
    async def test_global_away_forces_away(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test global away sensor forces AWAY."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            None,
            None,
            None,
            "binary_sensor.house_empty",
        )

        await manager._async_update_schedule(None)
        assert manager._scheduled_preset == "present"

        # House empty
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.house_empty", STATE_ON
        )
        await manager._update_global_away_state()

        # Should override to away
        assert manager.get_active_preset() == "away"


class TestPriorityChain:
    """Test complete priority chain."""

    @pytest.mark.asyncio
    async def test_priority_window_highest(self, mock_hass, mock_state, mock_datetime):
        """Test window has highest priority."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.presence",
            "binary_sensor.window",
            "sensor.outdoor_temp",
            "binary_sensor.house_empty",
        )

        await manager._async_update_schedule(None)

        # Set all overrides active
        manager.set_manual_preset("cosy")
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.presence", STATE_ON
        )
        await manager._update_presence_state()

        mock_hass.states.get.return_value = mock_state("sensor.outdoor_temp", "25.0")
        await manager._update_outdoor_temp_state()

        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.house_empty", STATE_ON
        )
        await manager._update_global_away_state()

        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.window", STATE_ON
        )
        await manager._update_window_state()

        # Window should win
        assert manager.get_active_preset() == "off"

    @pytest.mark.asyncio
    async def test_priority_outdoor_temp_second(
        self, mock_hass, mock_state, mock_datetime
    ):
        """Test outdoor temp is second priority (after window)."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.presence",
            None,  # No window sensor
            "sensor.outdoor_temp",
            "binary_sensor.house_empty",
        )

        await manager._async_update_schedule(None)

        # Set all other overrides
        manager.set_manual_preset("cosy")
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.presence", STATE_ON
        )
        await manager._update_presence_state()

        mock_hass.states.get.return_value = mock_state("sensor.outdoor_temp", "25.0")
        await manager._update_outdoor_temp_state()

        # Outdoor temp should win
        assert manager.get_active_preset() == "off"

    @pytest.mark.asyncio
    async def test_priority_manual_third(self, mock_hass, mock_state, mock_datetime):
        """Test manual is third priority."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.presence",
            None,
            None,  # No outdoor temp
            "binary_sensor.house_empty",
        )

        await manager._async_update_schedule(None)

        # Manual preset
        manager.set_manual_preset("cosy")

        # Presence (would override away, but not manual)
        mock_hass.states.get.return_value = mock_state(
            "binary_sensor.presence", STATE_ON
        )
        await manager._update_presence_state()

        # Manual should win
        assert manager.get_active_preset() == "cosy"


class TestOverrideStatus:
    """Test override status reporting."""

    @pytest.mark.asyncio
    async def test_get_override_status(self, mock_hass, mock_state, mock_datetime):
        """Test getting override status for UI."""
        mock_datetime.set_time(datetime(2024, 1, 15, 19, 0))

        schedule_config = {"weekday": [{"time": "17:00", "preset": "present"}]}

        manager = PresetManager(
            mock_hass,
            "Test",
            schedule_config,
            "binary_sensor.presence",
            "binary_sensor.window",
            "sensor.outdoor_temp",
            "binary_sensor.house_empty",
        )

        await manager._async_update_schedule(None)
        manager.set_manual_preset("cosy")

        status = manager.get_override_status()

        assert status["scheduled_preset"] == "present"
        assert status["manual_override"] == "cosy"
        assert status["presence_override"] is False
        assert status["window_open"] is False
        assert status["outdoor_temp_high"] is False
        assert status["global_away"] is False
