# Simple Thermostat

A simple, effective Home Assistant thermostat integration for Bosch BTH-RA TRVs with **hybrid binary + proportional control**.

## Why Simple Thermostat?

**Problem with Better Thermostat:** Complex algorithms (PID/MPC/TPI) calculate intermediate temperatures that prevent valves from opening fully, resulting in "always set to low temperatures and heater never on full power."

**Solution:** Simple Thermostat uses a hybrid approach:
- **Binary control** (0% or 100%) when far from target → Fast heating with full power
- **Proportional control** when near target (±0.5°C) → Smooth temperature maintenance
- **No complex algorithms** → Simple, predictable, debuggable

## Features

✅ **Hybrid Control Strategy**
- Binary 100% valve when >0.5°C below target
- Proportional TRV control when within ±0.5°C of target
- Binary 0% valve when >0.5°C above target

✅ **Multi-TRV Support**
- Control multiple TRVs as one thermostat
- All valves synchronized

✅ **Three Preset Modes**
- AWAY: Lower temperature when away
- PRESENT: Normal comfortable temperature
- COSY: Extra warm temperature

✅ **External Temperature Sensor**
- Uses accurate room sensor, not TRV's internal sensor
- Optionally syncs external temp to TRV every 25 minutes

✅ **Diagnostic Sensors for Graphs**
- Control mode sensor (binary_heat/proportional/binary_cool)
- Temperature error sensor
- Per-TRV internal temp, target temp, heating status
- Perfect for ApexCharts visualization

✅ **Simple Configuration**
- YAML-only configuration
- No complex UI config flow
- ~300 lines of code vs 4000+ in Better Thermostat

## Requirements

- Home Assistant
- Bosch BTH-RA TRVs connected via Zigbee2MQTT
- External temperature sensor in each room
- MQTT integration configured

## Installation

Install via HACS custom repository:

1. Open **HACS → Integrations**
2. Click **⋮** (three dots, top right)
3. Click **Custom repositories**
4. Add:
   - **Repository:** `https://github.com/moritzhoppner1/simple_thermostat`
   - **Category:** Integration
5. Click **Add**
6. Search "Simple Thermostat" in HACS
7. Click **Download**
8. Restart Home Assistant

The custom card is automatically registered - no manual resource configuration needed!

## Configuration

### Finding Your Entity IDs

Before configuring, you need to find your TRV entity IDs in Home Assistant:

1. **Go to Developer Tools → States**
2. **Search for your room name** (e.g., "kaminzimmer" or "living room")
3. **Look for these entities:**
   - **External temperature sensor:** `sensor.ROOM_temperature` (your room temperature sensor)
   - **TRV climate entities:** `climate.ROOM_trv` or similar
   - **TRV valve position:** `number.ROOM_trv_pi_heating_demand`

**Example for "Kaminzimmer":**
- Temperature sensor: `sensor.kaminzimmer_temperature`
- Climate entity: `climate.kaminzimmer_trv`
- Valve position: `number.kaminzimmer_trv_pi_heating_demand`

### Add to your `configuration.yaml`

**Simple configuration (recommended):**

```yaml
climate:
  - platform: simple_thermostat
    name: "Living Room"
    unique_id: "living_room_thermostat"

    # External temperature sensor
    temperature_sensor: sensor.living_room_temperature

    # TRV IDs (automatically creates valve and climate entities)
    trv_ids:
      - living_room_trv
    # Auto-constructs:
    #   number.living_room_trv_pi_heating_demand (valve)
    #   climate.living_room_trv (climate)

    # Preset temperatures (°C)
    away_temp: 18.0
    present_temp: 21.0
    cosy_temp: 23.0

    # Control thresholds
    binary_threshold: 0.5
    hysteresis: 0.3

    # Remote temperature sync
    sync_remote_temp: true

    # Initial preset
    initial_preset: present
```

**Advanced configuration (explicit entity IDs):**

If your TRV entities don't follow the standard naming pattern, use explicit entity IDs:

```yaml
climate:
  - platform: simple_thermostat
    name: "Living Room"
    temperature_sensor: sensor.living_room_temperature

    # Explicit entity IDs
    valve_entities:
      - number.custom_valve_name_pi_heating_demand
    climate_entities:
      - climate.custom_climate_name

    away_temp: 18.0
    present_temp: 21.0
    cosy_temp: 23.0
```

### Configuration Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `name` | Yes | - | Thermostat name |
| `temperature_sensor` | Yes | - | External room temperature sensor |
| `valve_entities` | Yes | - | List of TRV valve position entities |
| `climate_entities` | Yes | - | List of TRV climate entities |
| `away_temp` | Yes | - | AWAY preset temperature (°C) |
| `present_temp` | Yes | - | PRESENT preset temperature (°C) |
| `cosy_temp` | Yes | - | COSY preset temperature (°C) |
| `binary_threshold` | No | 0.5 | Use binary control when error > threshold |
| `hysteresis` | No | 0.3 | Prevent rapid cycling |
| `sync_remote_temp` | No | true | Send external temp to TRV every 25min |
| `initial_preset` | No | present | Initial preset mode on startup |
| `unique_id` | No | - | Unique ID for entity |

## How It Works

### Control Zones

```
Temperature Error (target - current):

> +0.5°C  →  BINARY HEAT MODE
              - Valve: 100% (fully open)
              - TRV Target: 30°C (max)
              - Result: Fast heating with full power

±0.5°C    →  PROPORTIONAL MODE
              - TRV Target: Calculated from external sensor
              - Valve: Controlled by TRV
              - Result: Smooth temperature control

< -0.5°C  →  BINARY COOL MODE
              - Valve: 0% (closed)
              - TRV Target: 5°C (min)
              - Result: Heating stopped
```

### Proportional Mode Calculation

When within ±0.5°C of target:

```python
TRV_target = (room_target - external_temp) + trv_internal_temp
```

**Example:**
- Want room at 21°C
- External sensor reads 20.7°C
- TRV internal sensor reads 22°C
- **TRV target = (21 - 20.7) + 22 = 22.3°C**

The TRV will modulate the valve to bring its sensor from 22°C to 22.3°C, which brings the room from 20.7°C to 21°C.

## Entities Created

For a thermostat named "Living Room" with 2 TRVs:

### Main Climate Entity
- `climate.living_room`

### Diagnostic Sensors
- `sensor.living_room_control_mode`
- `sensor.living_room_temperature_error`
- `binary_sensor.living_room_heating`

### Per-TRV Sensors
- `sensor.living_room_trv_1_internal_temp`
- `sensor.living_room_trv_1_target_temp`
- `binary_sensor.living_room_trv_1_heating`
- `sensor.living_room_trv_2_internal_temp`
- `sensor.living_room_trv_2_target_temp`
- `binary_sensor.living_room_trv_2_heating`

## Usage

### Custom Card (All-in-One - Recommended!)

The integration includes a custom card that shows **everything in one place**:
- Thermostat control with preset buttons
- Current status (control mode, temperature error, heating status)
- Collapsible action history logs (hidden by default)

**Step 1: Add Resource (ONE TIME SETUP)**

Go to: **Settings → Dashboards → Resources** (top right menu) and add:

```
URL: /simple_thermostat/simple-thermostat-card.js
Type: JavaScript Module
```

**Step 2: Use the Card**

Add to your dashboard (one line per thermostat!):

```yaml
type: custom:simple-thermostat-card
entity: climate.living_room
```

That's it! The card automatically:
- Finds all related sensors
- Shows temperature control with +/- buttons
- Displays preset mode buttons (AWAY/PRESENT/COSY)
- Shows control mode, temperature error, heating status
- Includes collapsible logs (click "Recent Actions" to expand)

### Via Standard UI Card

You can also use the standard Home Assistant thermostat card:

```yaml
type: thermostat
entity: climate.living_room
```

### Via Service Calls

**Set preset mode:**
```yaml
service: climate.set_preset_mode
target:
  entity_id: climate.living_room
data:
  preset_mode: cosy
```

**Set temperature (clears preset):**
```yaml
service: climate.set_temperature
target:
  entity_id: climate.living_room
data:
  temperature: 22.5
```

**Turn on/off:**
```yaml
service: climate.set_hvac_mode
target:
  entity_id: climate.living_room
data:
  hvac_mode: heat  # or 'off'
```

## Visualization

See `apexcharts-card.yaml.example` for detailed graph configurations.

### Basic Graph

```yaml
type: custom:apexcharts-card
header:
  title: Living Room Heating
graph_span: 24h
series:
  - entity: sensor.living_room_temperature
    name: Room Temp
  - entity: climate.living_room
    attribute: temperature
    name: Target
  - entity: number.living_room_trv_pi_heating_demand
    name: Valve Position
    yaxis_id: percent
```

## Troubleshooting

### TRVs not responding

**Check MQTT topics:**
```bash
mosquitto_sub -h localhost -t 'zigbee2mqtt/#' -v
```

**Verify entity IDs:**
- Valve entities should be `number.*_pi_heating_demand`
- Climate entities should be `climate.*`

### Temperature not updating

**Check external sensor:**
```yaml
# In Developer Tools > States
sensor.living_room_temperature
```

Should show current temperature, not "unavailable"

### Valve always at 0% or 100%

**Check binary threshold:**
- Default 0.5°C may be too large/small for your room
- Adjust `binary_threshold` in configuration
- Monitor `sensor.living_room_temperature_error`

### Remote temperature not syncing

**Check MQTT entity naming:**
- Integration assumes Zigbee2MQTT naming: `zigbee2mqtt/FRIENDLY_NAME/set`
- Friendly name derived from climate entity ID
- Example: `climate.living_room_trv` → `zigbee2mqtt/living room trv/set`

**Manual test:**
```bash
mosquitto_pub -t 'zigbee2mqtt/living room trv/set' \
              -m '{"remote_temperature": 21.5}'
```

## Debugging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.simple_thermostat: debug
```

Watch logs:
```bash
tail -f /config/home-assistant.log | grep simple_thermostat
```

## Comparison with Other Thermostats

| Feature | Simple Thermostat | Better Thermostat | Awesome Thermostat |
|---------|-------------------|-------------------|-------------------|
| **Lines of Code** | ~400 | ~4000+ | ~676 |
| **Control Strategy** | Hybrid binary+proportional | Complex algorithms | Binary only |
| **Full Valve Opening** | ✅ Yes (binary mode) | ❌ No (always intermediate) | ✅ Yes |
| **Multi-TRV** | ✅ Yes | ✅ Yes | ❌ No |
| **Valve Position Control** | ✅ Yes | ✅ Yes | ❌ No (switches only) |
| **External Sensor** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Preset Modes** | 3 (AWAY/PRESENT/COSY) | Many | 7 |
| **Configuration** | YAML only | UI + YAML | YAML only |
| **Complexity** | Low | Very High | Low |
| **Diagnostic Sensors** | ✅ Yes | ✅ Yes | ❌ No |

## Examples

See:
- `configuration.yaml.example` - Full configuration examples
- `apexcharts-card.yaml.example` - Graph configurations

## Contributing

This is a private project for personal use. Feel free to fork and modify for your needs.

## License

MIT License - See LICENSE file

## Credits

Inspired by:
- [Awesome Thermostat](https://github.com/dadge/awesome_thermostat) - Simple binary control approach
- [Better Thermostat](https://github.com/KartoffelToby/better_thermostat) - Advanced features and multi-TRV support

Built specifically for Bosch BTH-RA TRVs based on analysis in the parent project's README.
