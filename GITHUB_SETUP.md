# GitHub Setup Guide

This guide shows how to publish Simple Thermostat to GitHub and install it from there.

## Publishing to GitHub

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `simple_thermostat`
3. Description: "Simple Thermostat for Home Assistant - Hybrid control for Bosch BTH-RA TRVs"
4. Public or Private (your choice)
5. **Do NOT** initialize with README (we have our own)
6. Click **Create repository**

### Step 2: Initialize Git (if not already done)

```bash
cd /Users/moritz/code/private/thermostate/simple_thermostat

# Initialize git repo
git init

# Add all files
git add .

# Make first commit
git commit -m "Initial commit: Simple Thermostat integration with custom card"
```

### Step 3: Push to GitHub

```bash
# Add your GitHub repo as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/simple_thermostat.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 4: Create Release (Optional but Recommended)

1. Go to your GitHub repo
2. Click **Releases → Create a new release**
3. Tag: `v1.1.0`
4. Title: `Simple Thermostat v1.1.0`
5. Description:
   ```markdown
   # Simple Thermostat v1.1.0

   Hybrid binary + proportional thermostat control for Bosch BTH-RA TRVs.

   ## Features
   - Hybrid control strategy (binary when far, proportional when near target)
   - Custom Lovelace card with one-line configuration
   - Action history logs
   - Multi-TRV support
   - Three preset modes (AWAY/PRESENT/COSY)

   ## Installation
   See README.md for installation instructions.
   ```
6. Click **Publish release**

## Installing from GitHub

Once published, users can install using:

### Method 1: Git Clone

```bash
cd /config/custom_components
git clone https://github.com/YOUR_USERNAME/simple_thermostat.git
cp -r simple_thermostat/custom_components/simple_thermostat .
rm -rf simple_thermostat
```

### Method 2: Direct Download

```bash
cd /config/custom_components
wget https://github.com/YOUR_USERNAME/simple_thermostat/archive/refs/heads/main.zip
unzip main.zip
mv simple_thermostat-main/custom_components/simple_thermostat .
rm -rf simple_thermostat-main main.zip
```

### Method 3: Git Submodule (for easy updates)

```bash
cd /config
git submodule add https://github.com/YOUR_USERNAME/simple_thermostat.git custom_components/simple_thermostat

# To update later:
cd /config
git submodule update --remote
```

## Repository Structure

Your GitHub repo should look like this:

```
simple_thermostat/                    (GitHub root)
├── README.md                         (Main documentation)
├── CUSTOM_CARD_README.md            (Card documentation)
├── IMPLEMENTATION_SUMMARY.md        (Technical details)
├── GITHUB_SETUP.md                  (This file)
├── LICENSE                           (Add MIT license)
├── configuration.yaml.example
├── dashboard-example.yaml
├── apexcharts-card.yaml.example
└── custom_components/
    └── simple_thermostat/            (The integration)
        ├── __init__.py
        ├── manifest.json
        ├── climate.py
        ├── sensor.py
        └── www/
            └── simple-thermostat-card.js
```

## Adding to HACS (Optional)

If you want to make it available via HACS (Home Assistant Community Store):

### Step 1: Prepare Repository

1. Ensure your repo has:
   - ✅ `README.md` (done)
   - ✅ `custom_components/simple_thermostat/` (done)
   - ✅ `custom_components/simple_thermostat/manifest.json` (done)
   - ✅ Releases with version tags (v1.1.0, etc.)

2. Create `hacs.json` in repo root:
   ```json
   {
     "name": "Simple Thermostat",
     "render_readme": true,
     "domains": ["climate", "sensor", "binary_sensor"]
   }
   ```

### Step 2: Submit to HACS

1. Fork https://github.com/hacs/default
2. Edit `custom_components.json`
3. Add your repo:
   ```json
   {
     "simple_thermostat": {
       "name": "Simple Thermostat",
       "repository": "YOUR_USERNAME/simple_thermostat",
       "category": "integration"
     }
   }
   ```
4. Create Pull Request
5. Wait for approval

### Step 3: Users Install via HACS

Once approved, users can:
1. Open HACS in Home Assistant
2. Click **Integrations**
3. Click **Explore & Download Repositories**
4. Search for "Simple Thermostat"
5. Click **Download**

## Updating the Integration

### Making Changes

```bash
cd /Users/moritz/code/private/thermostate/simple_thermostat

# Make your changes
# ...

# Commit changes
git add .
git commit -m "Description of changes"

# Push to GitHub
git push
```

### Creating New Release

1. Update version in `manifest.json`:
   ```json
   {
     "version": "1.2.0"
   }
   ```

2. Commit and push:
   ```bash
   git add custom_components/simple_thermostat/manifest.json
   git commit -m "Bump version to 1.2.0"
   git push
   ```

3. Create new release on GitHub:
   - Tag: `v1.2.0`
   - Title: `Simple Thermostat v1.2.0`
   - Description: List of changes

### Users Update

**If installed via git clone:**
```bash
cd /config/custom_components
rm -rf simple_thermostat
git clone https://github.com/YOUR_USERNAME/simple_thermostat.git
cp -r simple_thermostat/custom_components/simple_thermostat .
rm -rf simple_thermostat
```

**If installed via HACS:**
- HACS → Integrations → Simple Thermostat → Update

**If installed as submodule:**
```bash
cd /config
git submodule update --remote
```

Then restart Home Assistant.

## Adding a License

Create `LICENSE` file in repo root:

```
MIT License

Copyright (c) 2025 YOUR_NAME

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## GitHub Actions (Optional)

Create `.github/workflows/validate.yml` for automatic validation:

```yaml
name: Validate

on:
  push:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: HACS Validation
        uses: hacs/action@main
        with:
          category: integration
```

## Documentation in GitHub

Your GitHub repo will show `README.md` on the main page. Make sure it includes:
- ✅ Installation instructions (done)
- ✅ Configuration examples (done)
- ✅ Features list (done)
- ✅ Usage examples (done)
- ✅ Troubleshooting (done)

Users visiting your GitHub repo will see everything they need to get started!

## Quick Setup Checklist

- [ ] Create GitHub repository
- [ ] Initialize git and push code
- [ ] Create first release (v1.1.0)
- [ ] Add LICENSE file
- [ ] Update README with GitHub URLs
- [ ] (Optional) Create hacs.json
- [ ] (Optional) Submit to HACS
- [ ] (Optional) Add GitHub Actions

## Example Installation Command for Users

Once published, users can install with:

```bash
# Simple one-liner
cd /config/custom_components && \
  wget -qO- https://github.com/YOUR_USERNAME/simple_thermostat/archive/refs/heads/main.tar.gz | \
  tar xz --strip-components=2 simple_thermostat-main/custom_components/simple_thermostat && \
  echo "Installation complete! Restart Home Assistant."
```

Or the more readable version from the README.

## Support

After publishing, you can provide support via:
- GitHub Issues: https://github.com/YOUR_USERNAME/simple_thermostat/issues
- GitHub Discussions: https://github.com/YOUR_USERNAME/simple_thermostat/discussions
- Home Assistant Community Forum

## Summary

1. **Publish:** `git push` to GitHub
2. **Release:** Create release with version tag
3. **Install:** Users clone or download from GitHub
4. **Update:** Push changes, create new release
5. **HACS (Optional):** Submit for easier installation

Your integration is now shareable and installable from GitHub!
