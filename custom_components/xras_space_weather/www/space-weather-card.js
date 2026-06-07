console.info(
  "%c 🌌 SPACE-WEATHER-CARD %c v3.0.1 (Ultimate) ",
  "color: white; background: #1c1c1c; font-weight: 700;",
  "color: white; background: #9c27b0; font-weight: 700;"
);

const TRANSLATIONS = {
  en: {
    tabs: { summary: "Summary", details: "Details", forecast: "Forecast" },
    aurora_title: "Auroras", ai_label: "Activity Index:", prob_label: "Probability at location:",
    storms_title: "Magnetic Storms", max_today: "Maximum today:", tmrw: "Expected tomorrow:",
    solar_title: "Solar Activity", f10_label: "F10.7 Index:", status_label: "Status:",
    flare_label: "Last flare:", loc_default: "Location", norm_status: "Normal (No storms)",
    g1_status: "G1 (Minor storm)", g2_status: "G2 (Moderate storm)", g3_status: "G3 (Strong storm)",
    g4_status: "G4 (Severe storm)", g5_status: "G5 (Extreme storm)", at_time: "at",
    desc_norm: "(Normal)", desc_storm: "Storm G", card_name: "Space Weather",
    card_desc: "Ultimate card for IKI RAN space weather",
    editor: { title: "Card Setup", city_label: "City Override", layout_label: "Style", layout_tabs: "Tabs", layout_classic: "Classic" }
  },
  ru: {
    tabs: { summary: "Сводка", details: "Детали", forecast: "Прогноз" },
    aurora_title: "Полярные сияния", ai_label: "Индекс активности (AI):", prob_label: "Вероятность в локации:",
    storms_title: "Магнитные бури", max_today: "Максимум сегодня:", tmrw: "Ожидается завтра:",
    solar_title: "Солнечная активность", f10_label: "Индекс излучения (F10.7):", status_label: "Статус:",
    flare_label: "Последняя вспышка:", loc_default: "Локация", norm_status: "Норма (Без бурь)",
    g1_status: "G1 (Слабая буря)", g2_status: "G2 (Умеренная буря)", g3_status: "G3 (Сильная буря)",
    g4_status: "G4 (Очень сильно)", g5_status: "G5 (Экстремально)", at_time: "на",
    desc_norm: "(Норма)", desc_storm: "Буря G", card_name: "Космическая погода",
    card_desc: "Универсальная карточка ИКИ РАН",
    editor: { title: "Настройка карточки", city_label: "Город (Необязательно)", layout_label: "Стиль", layout_tabs: "Вкладки", layout_classic: "Классика" }
  }
};

const LitElement = Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

class SpaceWeatherCard extends LitElement {
  static get properties() { return { hass: { type: Object }, config: { type: Object }, _activeTab: { type: String, state: true } }; }
  constructor() { super(); this._activeTab = 'summary'; }
  setConfig(config) { if (!config) throw new Error("Invalid config"); this.config = { layout: "tabs", ...config }; }
  getCardSize() { return this.config.layout === 'classic' ? 8 : 6; }
  static getConfigElement() { return document.createElement("space-weather-card-editor"); }
  get t() { const lang = (this.hass?.language || 'en').substring(0, 2); return TRANSLATIONS[lang] || TRANSLATIONS['en']; }

  _getEntityData(suffix) {
    if (!this.hass) return { state: '--', time: '--:--', attributes: {} };
    let entityId = this.config[`entity_${suffix}`];
    if (!entityId) { for (let eid in this.hass.states) { if (eid.includes(suffix)) { entityId = eid; break; } } }
    if (entityId && this.hass.states[entityId]) {
      const stateObj = this.hass.states[entityId];
      let timeStr = '--:--';
      if (stateObj.last_updated) {
        try { const d = new Date(stateObj.last_updated.replace(' ', 'T')); if (!isNaN(d.getTime())) timeStr = d.toLocaleTimeString(this.hass.language || 'ru-RU', { hour: '2-digit', minute: '2-digit' }); } catch(e) {}
      }
      return { state: String(stateObj.state), time: timeStr, attributes: stateObj.attributes || {} };
    }
    return { state: '--', time: '--:--', attributes: {} };
  }

  _getKpDesc(val) {
    const n = parseFloat(val);
    if (isNaN(n)) return '';
    if (n < 5) return this.t.desc_norm;
    return `(${this.t.desc_storm}${Math.floor(n - 4)})`;
  }

  render() {
    if (!this.hass || !this.config) return html``;
    const ai = this._getEntityData('aurora_index_latest'), aurora = this._getEntityData('aurora_probability_local'), kp = this._getEntityData('kp_current'), kpToday = this._getEntityData('kp_forecast_today'), kpTmrw = this._getEntityData('kp_forecast_tomorrow'), f10 = this._getEntityData('f10_forecast_today'), flaresStatus = this._getEntityData('solar_flare_current_status'), flaresLast = this._getEntityData('solar_flare_last_info');
    let cityName = aurora.attributes.location_name || this.config.city || this.t.loc_default;
    if (this.config.city) cityName = this.config.city;
    const kpNum = parseFloat(kp.state);
    let videoUrl = '/api/xras_sw_static/normal.mp4', statusName = this.t.norm_status, badgeColor = 'var(--success-color, #4caf50)';
    if (!isNaN(kpNum)) {
      if (kpNum >= 9) { videoUrl = '/api/xras_sw_static/g5.mp4'; statusName = this.t.g5_status; badgeColor = 'var(--error-color, #f44336)'; }
      else if (kpNum >= 5) { videoUrl = '/api/xras_sw_static/g1.mp4'; statusName = this.t.g1_status; badgeColor = 'var(--warning-color, #ff9800)'; }
    }

    const renderHeader = () => html`
      <div class="header-container">
        <video id="bg-video" class="bg-video" src=${videoUrl} autoplay loop muted playsinline webkit-playsinline disablePictureInPicture disableRemotePlayback></video>
        <div class="header-overlay">
          <div class="kp-city"><ha-icon icon="mdi:map-marker" style="--mdc-icon-size: 14px; margin-right: 4px;"></ha-icon>${cityName}</div>
          <div class="kp-main">${kp.state} <span style="font-size: 18px;">Kp</span></div>
          <div class="kp-desc"><span class="status-badge" style="background-color: ${badgeColor};"></span>${statusName}</div>
        </div>
      </div>
    `;

    const renderDetails = () => html`
      <div class="section-title"><ha-icon icon="mdi:aurora"></ha-icon> ${this.t.aurora_title}</div>
      <div class="tile-row"><span class="label">${this.t.ai_label}</span><span class="value">${ai.state} <span class="desc">(${this.t.at_time} ${ai.time})</span></span></div>
      <div class="tile-row"><span class="label">${this.t.prob_label}</span><span class="value">${aurora.state}%</span></div>
      <div class="section-title" style="margin-top: 16px;"><ha-icon icon="mdi:white-balance-sunny"></ha-icon> ${this.t.solar_title}</div>
      <div class="tile-row"><span class="label">${this.t.f10_label}</span><span class="value">${f10.state}</span></div>
      <div class="tile-col"><span class="label">${this.t.status_label}</span><span class="value font-normal">${flaresStatus.state}</span></div>
      <div class="tile-col"><span class="label">${this.t.flare_label}</span><span class="value font-normal">${flaresLast.state}</span></div>
    `;

    const renderForecast = () => html`
      <div class="section-title"><ha-icon icon="mdi:magnet"></ha-icon> ${this.t.storms_title}</div>
      <div class="tile-row"><span class="label">${this.t.max_today}</span><span class="value">${kpToday.state} <span class="desc">${this._getKpDesc(kpToday.state)}</span></span></div>
      <div class="tile-row" style="margin-top: 8px;"><span class="label">${this.t.tmrw}</span><span class="value">${kpTmrw.state} <span class="desc">${this._getKpDesc(kpTmrw.state)}</span></span></div>
    `;

    return this.config.layout === 'classic' ? html`<ha-card>${renderHeader()}<div class="content-body">${renderDetails()}${renderForecast()}</div></ha-card>` : html`<ha-card><div class="tabs-container"><div class="tab ${this._activeTab === 'summary' ? 'active' : ''}" @click=${() => this._activeTab = 'summary'}><ha-icon icon="mdi:earth"></ha-icon> ${this.t.tabs.summary}</div><div class="tab ${this._activeTab === 'details' ? 'active' : ''}" @click=${() => this._activeTab = 'details'}><ha-icon icon="mdi:chart-bar"></ha-icon> ${this.t.tabs.details}</div><div class="tab ${this._activeTab === 'forecast' ? 'active' : ''}" @click=${() => this._activeTab = 'forecast'}><ha-icon icon="mdi:calendar-clock"></ha-icon> ${this.t.tabs.forecast}</div></div><div class="tab-content">${this._activeTab === 'summary' ? renderHeader() : ''}${this._activeTab === 'details' ? html`<div class="content-body">${renderDetails()}</div>` : ''}${this._activeTab === 'forecast' ? html`<div class="content-body">${renderForecast()}</div>` : ''}</div></ha-card>`;
  }

  static get styles() { return css`ha-card{overflow:hidden;display:flex;flex-direction:column;background:var(--card-background-color);border-radius:var(--ha-card-border-radius,12px)}.tabs-container{display:flex;justify-content:space-around;background:var(--secondary-background-color);border-bottom:1px solid var(--divider-color,rgba(0,0,0,0.1))}.tab{flex:1;text-align:center;padding:12px 0;cursor:pointer;font-size:13px;font-weight:500;color:var(--secondary-text-color);transition:background-color .2s;display:flex;align-items:center;justify-content:center;gap:6px}.tab ha-icon{--mdc-icon-size:18px}.tab:hover{background:var(--primary-background-color)}.tab.active{color:var(--primary-color);border-bottom:2px solid var(--primary-color);background:transparent}.header-container{width:100%;height:180px;position:relative;display:flex;align-items:flex-end;background-color:#000;overflow:hidden}.bg-video{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:0;pointer-events:none}.header-overlay{width:100%;position:relative;z-index:1;background:linear-gradient(to top,rgba(0,0,0,.85) 0%,rgba(0,0,0,.2) 70%,transparent 100%);padding:16px;color:white}.kp-city{font-size:12px;font-weight:500;opacity:.9;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;display:flex;align-items:center}.kp-main{font-size:42px;font-weight:bold;line-height:1;text-shadow:1px 1px 4px rgba(0,0,0,.8)}.kp-desc{font-size:16px;font-weight:500;margin-top:6px;text-shadow:1px 1px 2px rgba(0,0,0,.8);display:flex;align-items:center;gap:8px}.status-badge{width:10px;height:10px;border-radius:50%;display:inline-block;box-shadow:0 0 4px rgba(0,0,0,.5)}.content-body{padding:16px;display:flex;flex-direction:column;gap:8px}.section-title{font-size:16px;font-weight:500;color:var(--primary-text-color);display:flex;align-items:center;gap:8px;margin-bottom:4px}.section-title ha-icon{color:var(--primary-color)}.tile-row{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:var(--secondary-background-color);border-radius:var(--ha-card-border-radius,12px);margin-bottom:4px}.tile-col{display:flex;flex-direction:column;gap:4px;padding:12px 16px;background:var(--secondary-background-color);border-radius:var(--ha-card-border-radius,12px);margin-bottom:4px}.label{color:var(--secondary-text-color);font-size:14px}.value{color:var(--primary-text-color);font-size:15px;font-weight:500}.font-normal{font-weight:normal}.desc{color:var(--secondary-text-color);font-size:13px;font-weight:normal;margin-left:4px}`; }
}
customElements.define('space-weather-card', SpaceWeatherCard);

class SpaceWeatherCardEditor extends LitElement {
  setConfig(config) { this._config = config; }
  get t() { const lang = (this.hass?.language || 'en').substring(0, 2); return TRANSLATIONS[lang] || TRANSLATIONS['en']; }
  render() {
    return html`<div class="card-config"><h3>${this.t.editor.title}</h3><select .value=${this._config.layout || "tabs"} .configValue=${"layout"} @change=${this._valueChanged} style="width:100%;padding:8px;border-radius:4px;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color)"><option value="tabs">${this.t.editor.layout_tabs}</option><option value="classic">${this.t.editor.layout_classic}</option></select><ha-textfield label="${this.t.editor.city_label}" .value=${this._config.city || ""} .configValue=${"city"} @input=${this._valueChanged}></ha-textfield></div>`;
  }
  _valueChanged(ev) {
    const target = ev.target;
    this._config = { ...this._config, [target.configValue]: target.value };
    this.dispatchEvent(new Event("config-changed", { bubbles: true, composed: true, detail: { config: this._config } }));
  }
  static get styles() { return css`.card-config { display: flex; flex-direction: column; gap: 16px; } ha-textfield { width: 100%; } `; }
}
customElements.define("space-weather-card-editor", SpaceWeatherCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'space-weather-card')) {
  const lang = (navigator.language || 'en').substring(0, 2);
  const t = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  window.customCards.push({ type: "space-weather-card", name: t.card_name, description: t.card_desc, preview: true });
}
