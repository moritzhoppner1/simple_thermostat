class SimpleThermostatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define an entity');
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;

    if (!this._initialized) {
      this._initialize();
      this._initialized = true;
    }

    this._updateContent();
  }

  _initialize() {
    const style = document.createElement('style');
    style.textContent = `
      :host {
        display: block;
      }

      .card-content {
        padding: 16px;
      }

      .card-title {
        font-size: 20px;
        font-weight: 500;
        margin-bottom: 16px;
        color: var(--primary-text-color, #000);
      }

      .thermostat-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding: 16px;
        background: var(--card-background-color, var(--ha-card-background, #fff));
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
      }

      .temperature-display {
        font-size: 48px;
        font-weight: 300;
        line-height: 1;
        color: var(--primary-text-color, #000);
      }

      .target-temp {
        font-size: 24px;
        color: var(--secondary-text-color, #666);
        margin-top: 8px;
        font-weight: 400;
      }

      .trv-temp {
        font-size: 14px;
        color: var(--secondary-text-color, #888);
        margin-top: 4px;
        font-weight: 300;
      }

      .controls {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .preset-buttons {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }

      .preset-button {
        flex: 1;
        padding: 12px;
        border: 2px solid var(--primary-color, #03a9f4);
        background: var(--card-background-color, #fff);
        color: var(--primary-color, #03a9f4);
        border-radius: var(--ha-card-border-radius, 8px);
        cursor: pointer;
        transition: all 0.2s;
        font-size: 14px;
        font-weight: 600;
      }

      .preset-button.active {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }

      .preset-button:hover {
        opacity: 0.8;
      }

      .status-section {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }

      .status-item {
        padding: 14px;
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 8px);
        border: 1px solid var(--divider-color, #e0e0e0);
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
      }

      .status-label {
        font-size: 11px;
        color: var(--secondary-text-color, #666);
        text-transform: uppercase;
        margin-bottom: 6px;
        font-weight: 600;
        letter-spacing: 0.5px;
      }

      .status-value {
        font-size: 20px;
        font-weight: 600;
        color: var(--primary-text-color, #000);
      }

      .status-value.heating {
        color: var(--error-color, #ff0000);
      }

      .override-indicator {
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .override-indicator.window {
        background: var(--error-color, #ff5252);
        color: white;
      }

      .override-indicator.outdoor-temp {
        background: var(--warning-color, #ff9800);
        color: white;
      }

      .override-indicator.manual {
        background: var(--info-color, #2196F3);
        color: white;
      }

      .override-indicator.presence {
        background: var(--success-color, #4CAF50);
        color: white;
      }

      .override-indicator.global-away {
        background: var(--disabled-color, #9E9E9E);
        color: white;
      }

      .override-indicator.schedule {
        background: var(--primary-color, #03A9F4);
        color: white;
      }

      .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
      }

      .details-section {
        margin-top: 16px;
        border-top: 1px solid var(--divider-color);
        padding-top: 16px;
      }

      .details-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        padding: 8px;
        margin-bottom: 8px;
      }

      .details-header:hover {
        background: var(--secondary-background-color);
        border-radius: 4px;
      }

      .details-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
      }

      .details-content.expanded {
        max-height: 1000px;
        overflow-y: auto;
      }

      .log-entry {
        padding: 8px;
        margin: 4px 0;
        background: var(--secondary-background-color);
        border-radius: 4px;
        font-size: 13px;
        font-family: monospace;
      }

      .log-time {
        color: var(--secondary-text-color);
        margin-right: 8px;
      }

      .button {
        padding: 10px 18px;
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
        border: none;
        border-radius: var(--ha-card-border-radius, 8px);
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        transition: all 0.2s;
      }

      .button:hover {
        opacity: 0.8;
      }

      .mode-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
      }

      .mode-badge.binary_heat {
        background: #ff5722;
        color: white;
      }

      .mode-badge.proportional {
        background: #4caf50;
        color: white;
      }

      .mode-badge.binary_cool {
        background: #2196f3;
        color: white;
      }

      .mode-badge.off {
        background: #757575;
        color: white;
      }

      .chart-section {
        margin: 16px 0;
      }

      .sliders-section {
        margin-top: 16px;
        padding: 16px;
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 8px);
        border: 1px solid var(--divider-color, #e0e0e0);
      }

      .sliders-header {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 16px;
        color: var(--primary-text-color, #000);
      }

      .slider-item {
        margin-bottom: 16px;
      }

      .slider-item:last-child {
        margin-bottom: 0;
      }

      .slider-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 13px;
        color: var(--secondary-text-color, #666);
      }

      .slider-label-name {
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .slider-label-value {
        font-weight: 600;
        color: var(--primary-text-color, #000);
        font-size: 14px;
      }

      input[type="range"] {
        width: 100%;
        height: 6px;
        border-radius: 3px;
        background: var(--divider-color, #e0e0e0);
        outline: none;
        -webkit-appearance: none;
      }

      input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--primary-color, #03a9f4);
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }

      input[type="range"]::-moz-range-thumb {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--primary-color, #03a9f4);
        cursor: pointer;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      }
    `;

    this.shadowRoot.appendChild(style);

    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="card-content">
        <div class="card-title" id="card-title"></div>
        <div class="thermostat-section" id="thermostat"></div>
        <div class="preset-buttons" id="presets"></div>
        <div class="details-section">
          <div class="details-header" id="details-toggle">
            <span><strong>Details</strong></span>
            <span id="details-icon">▼</span>
          </div>
          <div class="details-content" id="details-content">
            <div id="status"></div>
            <div id="chart"></div>
            <div id="logs"></div>
            <div id="sliders"></div>
          </div>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(card);

    // Add details toggle functionality
    const detailsToggle = this.shadowRoot.getElementById('details-toggle');
    const detailsContent = this.shadowRoot.getElementById('details-content');
    const detailsIcon = this.shadowRoot.getElementById('details-icon');

    detailsToggle.addEventListener('click', () => {
      detailsContent.classList.toggle('expanded');
      detailsIcon.textContent = detailsContent.classList.contains('expanded') ? '▲' : '▼';
    });
  }

  _updateContent() {
    if (!this._hass || !this._config.entity) return;

    const entityId = this._config.entity;
    const entity = this._hass.states[entityId];

    if (!entity) {
      this.shadowRoot.querySelector('.card-content').innerHTML =
        `<p>Entity ${entityId} not found</p>`;
      return;
    }

    // Extract base name for finding related sensors
    const baseName = entityId.replace('climate.', '');

    // Update title
    const titleSection = this.shadowRoot.getElementById('card-title');
    if (titleSection) {
      titleSection.textContent = entity.attributes.friendly_name || entityId;
    }

    // Update thermostat section
    this._updateThermostat(entity);

    // Update presets
    this._updatePresets(entity);

    // Update status
    this._updateStatus(baseName, entity);

    // Update sliders
    this._updateSliders(entity);

    // Update chart
    this._updateChart(baseName, entity);

    // Update logs
    this._updateLogs(entity);
  }

  _updateThermostat(entity) {
    const currentTemp = entity.attributes.current_temperature;
    const targetTemp = entity.attributes.temperature;

    // Extract base name and check heating status
    const entityId = this._config.entity;
    const baseName = entityId.replace('climate.', '');
    const heatingEntity = this._hass.states[`binary_sensor.${baseName}_heating`];
    const isHeating = heatingEntity ? heatingEntity.state === 'on' : false;

    // Get TRV internal temperature
    const trvTempSensors = this._findSensorsByPattern(baseName, 'internal_temp');
    let trvTemp = null;

    if (trvTempSensors.length > 0) {
      const state = this._hass.states[trvTempSensors[0]];
      if (state && state.state !== 'unavailable') {
        trvTemp = parseFloat(state.state);
      }
    }

    const thermostatSection = this.shadowRoot.getElementById('thermostat');
    thermostatSection.innerHTML = `
      <div>
        <div class="temperature-display">${currentTemp != null ? currentTemp.toFixed(1) : '--'}°C</div>
        <div class="target-temp">Target: ${targetTemp != null ? targetTemp.toFixed(1) : '--'}°C ${isHeating ? '🔥' : ''}</div>
        <div class="trv-temp">TRV: ${trvTemp != null ? trvTemp.toFixed(1) : '--'}°C</div>
      </div>
    `;
  }

  _updatePresets(entity) {
    const presets = entity.attributes.preset_modes || [];
    const currentPreset = entity.attributes.preset_mode;

    const presetsSection = this.shadowRoot.getElementById('presets');
    presetsSection.innerHTML = presets.map(preset => `
      <button class="preset-button ${preset === currentPreset ? 'active' : ''}"
              data-preset="${preset}">
        ${preset.toUpperCase()}
      </button>
    `).join('');

    // Add event listeners
    presetsSection.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', (e) => this._setPreset(e.target.dataset.preset));
    });
  }

  _updateStatus(baseName, entity) {
    const controlModeEntity = this._hass.states[`sensor.${baseName}_control_mode`];
    const tempErrorEntity = this._hass.states[`sensor.${baseName}_temperature_error`];
    const heatingEntity = this._hass.states[`binary_sensor.${baseName}_heating`];

    const controlMode = controlModeEntity ? controlModeEntity.state : 'unknown';
    const tempError = tempErrorEntity ? parseFloat(tempErrorEntity.state).toFixed(2) : '--';
    const isHeating = heatingEntity ? heatingEntity.state === 'on' : false;

    // Get override status from entity attributes
    const scheduledPreset = entity.attributes.scheduled_preset;
    const manualOverride = entity.attributes.manual_override;
    const presenceOverride = entity.attributes.presence_override;
    const windowOpen = entity.attributes.window_open;
    const outdoorTempHigh = entity.attributes.outdoor_temp_high;
    const globalAway = entity.attributes.global_away;

    // Build override indicators
    let overrideIndicators = '';

    if (windowOpen) {
      overrideIndicators += '<div class="override-indicator window">🪟 Window Open → Heating OFF</div>';
    }
    if (outdoorTempHigh) {
      overrideIndicators += '<div class="override-indicator outdoor-temp">🌡️ Outdoor Temp High → Heating OFF</div>';
    }
    if (manualOverride) {
      overrideIndicators += `<div class="override-indicator manual">✋ Manual: ${manualOverride.toUpperCase()}</div>`;
    }
    if (presenceOverride) {
      overrideIndicators += '<div class="override-indicator presence">👤 Presence Detected → PRESENT</div>';
    }
    if (globalAway) {
      overrideIndicators += '<div class="override-indicator global-away">🏠 House Empty → AWAY</div>';
    }
    if (scheduledPreset && !manualOverride && !presenceOverride && !windowOpen && !outdoorTempHigh && !globalAway) {
      overrideIndicators += `<div class="override-indicator schedule">📅 Schedule: ${scheduledPreset.toUpperCase()}</div>`;
    }

    const statusSection = this.shadowRoot.getElementById('status');
    statusSection.innerHTML = `
      ${overrideIndicators}
      <div class="status-item" title="${this._getControlModeTooltip(controlMode)}" style="margin-bottom: 16px;">
        <div class="status-label">Control Mode</div>
        <div class="status-value">
          <span class="mode-badge ${controlMode}">${controlMode.replace('_', ' ')}</span>
        </div>
      </div>
    `;
  }

  _getControlModeTooltip(mode) {
    const tooltips = {
      'binary_heat': 'Binary Heat: Room >0.5°C below target → Valve 100%, TRV 30°C (full power heating)',
      'proportional': 'Proportional: Room within ±0.5°C of target → TRV calculates precise valve position',
      'binary_cool': 'Binary Cool: Room >0.5°C above target → Valve 0%, TRV 5°C (heating off)',
      'off': 'Off: Heating disabled'
    };
    return tooltips[mode] || 'Unknown control mode';
  }

  _updateSliders(entity) {
    const awayTemp = entity.attributes.away_temp || 18;
    const presentTemp = entity.attributes.present_temp || 21;
    const cosyTemp = entity.attributes.cosy_temp || 23;

    const slidersSection = this.shadowRoot.getElementById('sliders');
    slidersSection.innerHTML = `
      <div class="sliders-header">Preset Temperatures</div>

      <div class="slider-item">
        <div class="slider-label">
          <span class="slider-label-name">Away</span>
          <span class="slider-label-value" id="away-value">${awayTemp.toFixed(1)}°C</span>
        </div>
        <input type="range" id="away-slider" min="10" max="25" step="0.5" value="${awayTemp}">
      </div>

      <div class="slider-item">
        <div class="slider-label">
          <span class="slider-label-name">Present</span>
          <span class="slider-label-value" id="present-value">${presentTemp.toFixed(1)}°C</span>
        </div>
        <input type="range" id="present-slider" min="10" max="25" step="0.5" value="${presentTemp}">
      </div>

      <div class="slider-item">
        <div class="slider-label">
          <span class="slider-label-name">Cosy</span>
          <span class="slider-label-value" id="cosy-value">${cosyTemp.toFixed(1)}°C</span>
        </div>
        <input type="range" id="cosy-slider" min="10" max="25" step="0.5" value="${cosyTemp}">
      </div>
    `;

    // Add event listeners for sliders
    const awaySlider = slidersSection.querySelector('#away-slider');
    const presentSlider = slidersSection.querySelector('#present-slider');
    const cosySlider = slidersSection.querySelector('#cosy-slider');

    awaySlider.addEventListener('input', (e) => {
      slidersSection.querySelector('#away-value').textContent = `${parseFloat(e.target.value).toFixed(1)}°C`;
    });

    awaySlider.addEventListener('change', (e) => {
      this._setPresetTemp('away_temp', parseFloat(e.target.value));
    });

    presentSlider.addEventListener('input', (e) => {
      slidersSection.querySelector('#present-value').textContent = `${parseFloat(e.target.value).toFixed(1)}°C`;
    });

    presentSlider.addEventListener('change', (e) => {
      this._setPresetTemp('present_temp', parseFloat(e.target.value));
    });

    cosySlider.addEventListener('input', (e) => {
      slidersSection.querySelector('#cosy-value').textContent = `${parseFloat(e.target.value).toFixed(1)}°C`;
    });

    cosySlider.addEventListener('change', (e) => {
      this._setPresetTemp('cosy_temp', parseFloat(e.target.value));
    });
  }

  _updateLogs(entity) {
    const logsSection = this.shadowRoot.getElementById('logs');
    const actionHistory = entity.attributes.action_history || [];

    if (actionHistory.length === 0) {
      logsSection.innerHTML = '<div style="padding: 8px; color: var(--secondary-text-color);">No recent actions</div>';
      return;
    }

    logsSection.innerHTML = `
      <div style="margin-top: 16px; border-top: 1px solid var(--divider-color); padding-top: 16px;">
        <div style="font-weight: 600; margin-bottom: 8px;">Recent Actions</div>
        ${actionHistory.slice(-10).reverse().map(action => {
          const time = action.time || '';
          const message = action.message || action;
          return `
            <div class="log-entry">
              <span class="log-time">${time}</span>
              <span>${message}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }


  _setPreset(preset) {
    this._hass.callService('climate', 'set_preset_mode', {
      entity_id: this._config.entity,
      preset_mode: preset
    });
  }

  _setPresetTemp(attribute, value) {
    this._hass.callService('simple_thermostat', 'set_preset_temperature', {
      entity_id: this._config.entity,
      [attribute]: value
    });
  }

  _updateChart(baseName, entity) {
    const chartSection = this.shadowRoot.getElementById('chart');

    // Check if ApexCharts card is available
    if (!customElements.get('apexcharts-card')) {
      chartSection.innerHTML = `
        <div style="padding: 12px; background: var(--warning-color, #ff9800); color: white; border-radius: 8px; text-align: center;">
          ⚠️ ApexCharts card not installed. Install via HACS to see the temperature graph.
        </div>
      `;
      return;
    }

    // Find temperature sensor from entity attributes
    console.log('Entity attributes:', entity.attributes);
    const tempSensorId = entity.attributes.temperature_sensor || `sensor.${baseName}_temperature`;
    console.log('Temperature sensor from attributes:', entity.attributes.temperature_sensor);
    console.log('Final tempSensorId:', tempSensorId);

    // Create ApexCharts card configuration
    const apexConfig = {
      type: 'custom:apexcharts-card',
      header: {
        show: true,
        title: `${entity.attributes.friendly_name} - Heating`,
        show_states: true,
        colorize_states: true
      },
      graph_span: '24h',
      hours_12: false,
      yaxis: [
        {
          id: 'temp',
          min: 10,
          max: 30,
          decimals: 1,
          apex_config: {
            title: { text: '°C' }
          }
        },
        {
          id: 'error',
          min: -3,
          max: 3,
          decimals: 1,
          opposite: true,
          apex_config: {
            title: { text: 'Error °C' }
          }
        },
        {
          id: 'percent',
          min: 0,
          max: 100,
          decimals: 0,
          opposite: true,
          apex_config: {
            title: { text: '%' }
          }
        },
        {
          id: 'status',
          min: 0,
          max: 1,
          show: false,
          opposite: true
        }
      ],
      series: this._getChartSeries(baseName, tempSensorId),
      apex_config: {
        chart: { height: 300 },
        legend: { show: true, position: 'bottom' },
        tooltip: { enabled: true, shared: true }
      }
    };

    // Create ApexCharts card element
    const apexCard = document.createElement('apexcharts-card');
    apexCard.setConfig(apexConfig);
    apexCard.hass = this._hass;

    // Clear and add chart
    chartSection.innerHTML = '';
    chartSection.appendChild(apexCard);
  }

  _findSensorsByPattern(baseName, suffix) {
    const pattern = new RegExp(`^sensor\\.${baseName.replace('.', '\\.')}_.*_${suffix}$`);
    return Object.keys(this._hass.states).filter(id => pattern.test(id));
  }

  _getChartSeries(baseName, tempSensorId) {
    const series = [];

    console.log('Building chart series for baseName:', baseName);
    console.log('Temperature sensor ID:', tempSensorId);

    // Room temperature (external sensor)
    if (this._hass.states[tempSensorId]) {
      console.log('✓ Found room temp sensor:', tempSensorId);
      series.push({
        entity: tempSensorId,
        name: 'Room Temp',
        color: '#4CAF50',
        stroke_width: 3,
        yaxis_id: 'temp'
      });
    } else {
      console.log('✗ Room temp sensor not found:', tempSensorId);
    }

    // Target temperature
    series.push({
      entity: `climate.${baseName}`,
      attribute: 'temperature',
      name: 'Target',
      color: '#FF9800',
      stroke_width: 2,
      curve: 'stepline',
      yaxis_id: 'temp'
    });

    // Temperature error
    const tempErrorSensor = `sensor.${baseName}_temperature_error`;
    if (this._hass.states[tempErrorSensor]) {
      series.push({
        entity: tempErrorSensor,
        name: 'Error',
        color: '#E91E63',
        stroke_width: 2,
        yaxis_id: 'error'
      });
    }

    // TRV internal temp
    const trvTempSensors = this._findSensorsByPattern(baseName, 'internal_temp');
    console.log('Found TRV temp sensors:', trvTempSensors);

    if (trvTempSensors.length > 0) {
      const sensor = trvTempSensors[0];
      console.log('✓ Using TRV temp sensor:', sensor);
      series.push({
        entity: sensor,
        name: 'TRV Temp',
        color: '#9C27B0',
        stroke_width: 2,
        yaxis_id: 'temp',
        opacity: 0.7
      });
    } else {
      console.log('✗ No TRV temp sensors found');
    }

    // TRV target temp
    const trvTargetSensors = this._findSensorsByPattern(baseName, 'target_temp');
    console.log('Found TRV target sensors:', trvTargetSensors);

    if (trvTargetSensors.length > 0) {
      const sensor = trvTargetSensors[0];
      console.log('✓ Using TRV target sensor:', sensor);
      series.push({
        entity: sensor,
        name: 'TRV Target',
        color: '#673AB7',
        stroke_width: 1,
        curve: 'stepline',
        yaxis_id: 'temp',
        opacity: 0.6
      });
    } else {
      console.log('✗ No TRV target sensors found');
    }

    // Valve position
    const valveSensors = this._findSensorsByPattern(baseName, 'valve_position');
    console.log('Found valve sensors:', valveSensors);

    if (valveSensors.length > 0) {
      const sensor = valveSensors[0];
      console.log('✓ Using valve sensor:', sensor);
      series.push({
        entity: sensor,
        name: 'Valve',
        color: '#00BCD4',
        stroke_width: 2,
        curve: 'stepline',
        yaxis_id: 'percent'
      });
    } else {
      console.log('✗ No valve sensors found');
    }

    // Heating status - use the overall heating sensor
    const overallHeatingSensor = `binary_sensor.${baseName}_heating`;
    console.log('Checking overall heating sensor:', overallHeatingSensor);

    if (this._hass.states[overallHeatingSensor]) {
      console.log('✓ Found overall heating sensor:', overallHeatingSensor);
      series.push({
        entity: overallHeatingSensor,
        name: 'Heating',
        color: '#F44336',
        type: 'area',
        curve: 'stepline',
        stroke_width: 0,
        yaxis_id: 'status',
        opacity: 0.2,
        transform: "return x === 'on' ? 1 : 0;"
      });
    } else {
      console.log('✗ Overall heating sensor not found');
    }

    console.log('Total series added to chart:', series.length);
    console.log('Series:', series.map(s => s.name));

    return series;
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return {
      entity: 'climate.living_room'
    };
  }
}

customElements.define('simple-thermostat-card', SimpleThermostatCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'simple-thermostat-card',
  name: 'Simple Thermostat Card',
  description: 'All-in-one card for Simple Thermostat integration'
});

console.info(
  '%c SIMPLE-THERMOSTAT-CARD %c Version 1.0.0 ',
  'color: white; background: #039be5; font-weight: 700;',
  'color: #039be5; background: white; font-weight: 700;'
);
