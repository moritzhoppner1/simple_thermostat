# Installing Simple Thermostat from GitHub

Multiple ways to install Simple Thermostat directly from GitHub.

## Quick Summary

| Method | Difficulty | Updates | Best For |
|--------|-----------|---------|----------|
| One-liner script | ⭐ Easy | Manual | Quick install |
| Git clone | ⭐⭐ Moderate | Manual | Standard install |
| Git submodule | ⭐⭐⭐ Advanced | `git pull` | Developers |
| HACS | ⭐ Easy | Automatic | End users |

## Option 1: One-Liner Script (Easiest)

**Run this command in your Home Assistant host:**

```bash
bash <(curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh)
```

**What it does:**
1. Downloads latest version from GitHub
2. Extracts to `/config/custom_components/simple_thermostat/`
3. Cleans up temporary files
4. Shows next steps

**Custom config directory:**
```bash
HA_CONFIG_DIR=/home/homeassistant/.homeassistant bash <(curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh)
```

**To update:**
Run the same command again. It will replace the old installation.

---

## Option 2: Git Clone (Recommended for Git Users)

### Install

```bash
# Navigate to custom components
cd /config/custom_components

# Clone the repo
git clone https://github.com/YOUR_USERNAME/simple_thermostat.git temp_simple

# Copy just the integration
cp -r temp_simple/custom_components/simple_thermostat ./

# Clean up
rm -rf temp_simple
```

### Update

```bash
cd /config/custom_components
rm -rf simple_thermostat
git clone https://github.com/YOUR_USERNAME/simple_thermostat.git temp_simple
cp -r temp_simple/custom_components/simple_thermostat ./
rm -rf temp_simple
```

Or create a simple update script:

```bash
#!/bin/bash
# save as update_simple_thermostat.sh
cd /config/custom_components
rm -rf temp_simple simple_thermostat
git clone https://github.com/YOUR_USERNAME/simple_thermostat.git temp_simple
cp -r temp_simple/custom_components/simple_thermostat ./
rm -rf temp_simple
echo "✓ Updated! Restart Home Assistant."
```

---

## Option 3: Git Submodule (For Advanced Users)

**Pros:**
- Easy updates with `git pull`
- Track version in your Home Assistant config repo
- See exactly what changed between versions

**Cons:**
- Requires your Home Assistant config to be a git repository
- Slightly more complex setup

### Initial Setup

```bash
# Your /config must be a git repo
cd /config
git init  # if not already a repo

# Add as submodule
git submodule add https://github.com/YOUR_USERNAME/simple_thermostat.git custom_components/simple_thermostat

# Commit
git commit -m "Add Simple Thermostat as submodule"
```

### Update

```bash
cd /config
git submodule update --remote custom_components/simple_thermostat
git commit -am "Update Simple Thermostat"
```

### Clone Config on Another Machine

```bash
git clone --recurse-submodules https://github.com/yourusername/home-assistant-config.git /config
```

---

## Option 4: Direct Download (No Git Required)

### Using wget

```bash
cd /config/custom_components
wget https://github.com/YOUR_USERNAME/simple_thermostat/archive/refs/heads/main.tar.gz
tar xzf main.tar.gz
mv simple_thermostat-main/custom_components/simple_thermostat ./
rm -rf simple_thermostat-main main.tar.gz
```

### Using curl

```bash
cd /config/custom_components
curl -L https://github.com/YOUR_USERNAME/simple_thermostat/archive/refs/heads/main.tar.gz -o main.tar.gz
tar xzf main.tar.gz
mv simple_thermostat-main/custom_components/simple_thermostat ./
rm -rf simple_thermostat-main main.tar.gz
```

### From Web Browser

1. Go to: https://github.com/YOUR_USERNAME/simple_thermostat
2. Click **Code → Download ZIP**
3. Extract ZIP on your computer
4. Upload `custom_components/simple_thermostat/` to `/config/custom_components/` via:
   - Samba share
   - SSH/SCP
   - Home Assistant File Editor addon
   - VS Code SSH extension

---

## Option 5: HACS (When Available)

**Once submitted to HACS (see GITHUB_SETUP.md):**

1. Open Home Assistant
2. Go to **HACS → Integrations**
3. Click **Explore & Download Repositories**
4. Search: "Simple Thermostat"
5. Click **Download**
6. Restart Home Assistant

**Updates:** HACS will notify you when updates are available.

---

## Verification

After installation, verify:

### 1. Files Exist

```bash
ls -l /config/custom_components/simple_thermostat/
# Should show: __init__.py, climate.py, sensor.py, manifest.json, www/
```

### 2. Check Logs

```bash
tail -f /config/home-assistant.log | grep simple_thermostat
```

Should see:
```
INFO (MainThread) [custom_components.simple_thermostat] Registered Simple Thermostat card at /simple_thermostat/simple-thermostat-card.js
```

### 3. Check Version

```bash
grep version /config/custom_components/simple_thermostat/manifest.json
```

Should show: `"version": "1.1.0"` (or newer)

---

## Post-Installation

### 1. Configure Integration

Add to `/config/configuration.yaml`:

```yaml
climate:
  - platform: simple_thermostat
    name: "Living Room"
    temperature_sensor: sensor.living_room_temperature
    valve_entities:
      - number.living_room_trv_pi_heating_demand
    climate_entities:
      - climate.living_room_trv
    away_temp: 18.0
    present_temp: 21.0
    cosy_temp: 23.0
```

### 2. Restart Home Assistant

```bash
# Via CLI
ha core restart

# Or via UI
Settings → System → Restart
```

### 3. Enable Custom Card

**Settings → Dashboards → Resources → Add Resource**
- URL: `/simple_thermostat/simple-thermostat-card.js`
- Type: JavaScript Module

### 4. Add to Dashboard

```yaml
type: custom:simple-thermostat-card
entity: climate.living_room
```

---

## Troubleshooting GitHub Installation

### Error: "custom_components directory not found"

**Solution:**
```bash
mkdir -p /config/custom_components
```

### Error: "Permission denied"

**Solution:**
```bash
# Add sudo (if needed)
sudo bash <(curl -sSL https://...)

# Or change ownership
sudo chown -R homeassistant:homeassistant /config/custom_components
```

### Error: "wget: command not found"

**Solution:**
```bash
# Install wget
sudo apt-get update && sudo apt-get install -y wget

# Or use curl instead
curl -sSL https://... -o file.tar.gz
```

### Error: "git: command not found"

**Solution:**
```bash
# Install git
sudo apt-get update && sudo apt-get install -y git

# Or use download method instead
```

### Integration Not Showing

**Check:**
1. Files in correct location: `/config/custom_components/simple_thermostat/`
2. Restarted Home Assistant
3. No errors in logs: `grep simple_thermostat /config/home-assistant.log`

---

## Keeping Updated

### Check for Updates

**GitHub web interface:**
1. Visit https://github.com/YOUR_USERNAME/simple_thermostat
2. Check **Releases** for new versions
3. Compare with your installed version

**Command line:**
```bash
# Your installed version
grep version /config/custom_components/simple_thermostat/manifest.json

# Latest GitHub version
curl -s https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/custom_components/simple_thermostat/manifest.json | grep version
```

### Update Process

**Re-run installer:**
```bash
bash <(curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh)
```

**Or manually:**
```bash
cd /config/custom_components
rm -rf simple_thermostat
# Then re-download using any method above
```

**After update:**
1. Restart Home Assistant
2. Check logs for errors
3. Test your thermostats

---

## Uninstallation

### Remove Integration

```bash
# Remove files
rm -rf /config/custom_components/simple_thermostat

# Remove from configuration.yaml (manually edit file)

# Restart Home Assistant
```

### Remove Custom Card

**Settings → Dashboards → Resources**
- Find: `/simple_thermostat/simple-thermostat-card.js`
- Click trash icon
- Remove card from dashboard

---

## Best Practices

### For End Users
✅ Use: One-liner script or HACS
✅ Update: Re-run script or use HACS updates
✅ Backup: Take snapshot before updates

### For Developers
✅ Use: Git submodule
✅ Update: `git submodule update --remote`
✅ Contribute: Fork, modify, pull request

### For Testing
✅ Use: Git clone
✅ Update: Delete and re-clone
✅ Switch versions: `git checkout v1.0.0`

---

## FAQ

**Q: Do I need git installed?**
A: No, use the one-liner script or direct download methods.

**Q: Can I install specific version?**
A: Yes, replace `main` with version tag (e.g., `v1.1.0`) in URLs.

**Q: Will my configuration be deleted on update?**
A: No, configuration is in `configuration.yaml`, not in the integration folder.

**Q: Can I install in Docker/Supervised/OS?**
A: Yes, all methods work. Adjust `/config` path if needed.

**Q: How do I know what changed between versions?**
A: Check GitHub releases page or CHANGELOG.md (if available).

---

## Support

**Installation issues:**
- GitHub Issues: https://github.com/YOUR_USERNAME/simple_thermostat/issues
- Include: Installation method, error message, HA version

**General questions:**
- GitHub Discussions: https://github.com/YOUR_USERNAME/simple_thermostat/discussions
- Home Assistant Community Forum

---

## Summary Commands

**Quick Install:**
```bash
bash <(curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh)
```

**Quick Update:**
```bash
bash <(curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/simple_thermostat/main/install.sh)
```

**Quick Uninstall:**
```bash
rm -rf /config/custom_components/simple_thermostat
```

**Check Version:**
```bash
grep version /config/custom_components/simple_thermostat/manifest.json
```

Replace `YOUR_USERNAME` with actual GitHub username once published!
