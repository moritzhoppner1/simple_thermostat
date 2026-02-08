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

      .logs-section {
        margin-top: 16px;
        border-top: 1px solid var(--divider-color);
        padding-top: 16px;
      }

      .logs-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        padding: 8px;
        margin-bottom: 8px;
      }

      .logs-header:hover {
        background: var(--secondary-background-color);
        border-radius: 4px;
      }

      .logs-content {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
      }

      .logs-content.expanded {
        max-height: 300px;
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
    `;

    this.shadowRoot.appendChild(style);

    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="card-content">
        <div class="thermostat-section" id="thermostat"></div>
        <div class="preset-buttons" id="presets"></div>
        <div class="status-section" id="status"></div>
        <div class="chart-section" id="chart"></div>
        <div class="logs-section">
          <div class="logs-header" id="logs-toggle">
            <span><strong>Recent Actions</strong></span>
            <span id="logs-icon">▼</span>
          </div>
          <div class="logs-content" id="logs-content"></div>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(card);

    // Add logs toggle functionality
    const logsToggle = this.shadowRoot.getElementById('logs-toggle');
    const logsContent = this.shadowRoot.getElementById('logs-content');
    const logsIcon = this.shadowRoot.getElementById('logs-icon');

    logsToggle.addEventListener('click', () => {
      logsContent.classList.toggle('expanded');
      logsIcon.textContent = logsContent.classList.contains('expanded') ? '▲' : '▼';
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

    // Update thermostat section
    this._updateThermostat(entity);

    // Update presets
    this._updatePresets(entity);

    // Update status
    this._updateStatus(baseName, entity);

    // Update logs
    this._updateLogs(entity);
  }

  _updateThermostat(entity) {
    const currentTemp = entity.attributes.current_temperature;
    const targetTemp = entity.attributes.temperature;
    const hvacMode = entity.state;

    const thermostatSection = this.shadowRoot.getElementById('thermostat');
    thermostatSection.innerHTML = `
      <div>
        <div class="temperature-display">${currentTemp !== undefined ? currentTemp.toFixed(1) : '--'}°C</div>
        <div class="target-temp">Target: ${targetTemp !== undefined ? targetTemp.toFixed(1) : '--'}°C</div>
      </div>
      <div class="controls">
        <button class="button" data-action="temp-up">+ 0.5°</button>
        <button class="button" data-action="temp-down">- 0.5°</button>
        <button class="button ${hvacMode === 'heat' ? 'active' : ''}" data-action="toggle">
          ${hvacMode === 'heat' ? 'ON' : 'OFF'}
        </button>
      </div>
    `;

    // Add event listeners
    thermostatSection.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', (e) => this._handleAction(e, entity));
    });
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

    const statusSection = this.shadowRoot.getElementById('status');
    statusSection.innerHTML = `
      <div class="status-item">
        <div class="status-label">Control Mode</div>
        <div class="status-value">
          <span class="mode-badge ${controlMode}">${controlMode.replace('_', ' ')}</span>
        </div>
      </div>
      <div class="status-item">
        <div class="status-label">Temperature Error</div>
        <div class="status-value">${tempError}°C</div>
      </div>
      <div class="status-item">
        <div class="status-label">Heating Status</div>
        <div class="status-value ${isHeating ? 'heating' : ''}">${isHeating ? '🔥 HEATING' : 'OFF'}</div>
      </div>
    `;
  }

  _updateLogs(entity) {
    const logsContent = this.shadowRoot.getElementById('logs-content');
    const actionHistory = entity.attributes.action_history || [];

    if (actionHistory.length === 0) {
      logsContent.innerHTML = '<div class="log-entry">No recent actions</div>';
      return;
    }

    logsContent.innerHTML = actionHistory.slice(-10).reverse().map(action => {
      const time = action.time || '';
      const message = action.message || action;
      return `
        <div class="log-entry">
          <span class="log-time">${time}</span>
          <span>${message}</span>
        </div>
      `;
    }).join('');
  }

  _handleAction(event, entity) {
    const action = event.target.dataset.action;
    const currentTemp = entity.attributes.temperature;

    switch (action) {
      case 'temp-up':
        this._setTemperature(currentTemp + 0.5);
        break;
      case 'temp-down':
        this._setTemperature(currentTemp - 0.5);
        break;
      case 'toggle':
        this._toggleHvac(entity.state);
        break;
    }
  }

  _setTemperature(temperature) {
    this._hass.callService('climate', 'set_temperature', {
      entity_id: this._config.entity,
      temperature: temperature
    });
  }

  _setPreset(preset) {
    this._hass.callService('climate', 'set_preset_mode', {
      entity_id: this._config.entity,
      preset_mode: preset
    });
  }

  _toggleHvac(currentMode) {
    const newMode = currentMode === 'heat' ? 'off' : 'heat';
    this._hass.callService('climate', 'set_hvac_mode', {
      entity_id: this._config.entity,
      hvac_mode: newMode
    });
  }

  getCardSize() {
    return 4;
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
