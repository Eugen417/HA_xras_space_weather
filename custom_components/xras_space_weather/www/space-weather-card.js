console.info(
  "%c 🌌 SPACE-WEATHER-CARD %c v2.0.1 (Classic) ",
  "color: white; background: #1c1c1c; font-weight: 700;",
  "color: white; background: #ff9800; font-weight: 700;"
);

const TRANSLATIONS_CLASSIC = {
  en: {
    aurora_title: "Auroras",
    ai_label: "Activity Index:",
    prob_label: "Probability at location:",
    storms_title: "Magnetic Storms",
    max_today: "Maximum today:",
    tmrw: "Expected tomorrow:",
    solar_title: "Solar Activity",
    f10_label: "Radiation Index (F10.7):",
    status_label: "Status:",
    flare_label: "Last flare:",
    loc_default: "Location",
    norm_status: "Normal (No storms)",
    g1_status: "G1 (Minor storm)",
    g2_status: "G2 (Moderate storm)",
    g3_status: "G3 (Strong storm)",
    g4_status: "G4 (Severe storm)",
    g5_status: "G5 (Extreme storm)",
    at_time: "at",
    desc_norm: "(Normal)",
    desc_storm: "Storm G",
    card_name: "Space Weather (Classic)",
    card_desc: "Modern single-page card for IKI RAN space weather",
    editor: { title: "Space Weather Card Setup", city_label: "City Name Override (Optional)" }
  },
  ru: {
    aurora_title: "Полярные сияния",
    ai_label: "Индекс активности:",
    prob_label: "Вероятность в локации:",
    storms_title: "Магнитные бури",
    max_today: "Максимум за сегодня:",
    tmrw: "Ожидается завтра:",
    solar_title: "Солнечная активность",
    f10_label: "Индекс излучения (F10.7):",
    status_label: "Статус:",
    flare_label: "Последняя вспышка:",
    loc_default: "Локация",
    norm_status: "Норма (Без бурь)",
    g1_status: "G1 (Слабая буря)",
    g2_status: "G2 (Умеренная буря)",
    g3_status: "G3 (Сильная буря)",
    g4_status: "G4 (Очень сильно)",
    g5_status: "G5 (Экстремально)",
    at_time: "на",
    desc_norm: "(Норма)",
    desc_storm: "Буря G",
    card_name: "Космическая погода (Классика)",
    card_desc: "Одностраничная карточка ИКИ РАН",
    editor: { title: "Настройка карточки космической погоды", city_label: "Название города (Необязательно)" }
  }
};

const LitElementClassic = Object.getPrototypeOf(customElements.get("ha-panel-lovelace"));
const htmlClassic = LitElementClassic.prototype.html;
const cssClassic = LitElementClassic.prototype.css;

class SpaceWeatherCardClassic extends LitElementClassic {
  static get properties() { return { hass: { type: Object }, config: { type: Object } }; }
  
  constructor() { super(); }
  setConfig(config) { if (!config) throw new Error("Invalid config"); this.config = config; }
  getCardSize() { return 8; }
  static getConfigElement() { return document.createElement("sw-card-classic-editor"); }
  static getStubConfig() { return { type: "custom:space-weather-card-classic", city: "" }; }
  
  get t() { const lang = (this.hass?.language || 'en').substring(0, 2); return TRANSLATIONS_CLASSIC[lang] || TRANSLATIONS_CLASSIC['en']; }

  _getEntityData(suffix) {
    if (!this.hass) return { state: '--', time: '--:--', attributes: {} };
    let entityId = this.config[`entity_${suffix}`];
    if (!entityId) {
        for (let eid in this.hass.states) { if (eid.includes(suffix)) { entityId = eid; break; } }
    }
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
    if (!this.hass || !this.config) return htmlClassic``;

    const ai = this._getEntityData('aurora_index_latest');
    const aurora = this._getEntityData('aurora_probability_local');
    const kp = this._getEntityData('kp_current');
    const kpToday = this._getEntityData('kp_forecast_today');
    const kpTmrw = this._getEntityData('kp_forecast_tomorrow');
    const f10 = this._getEntityData('f10_forecast_today');
    const flaresStatus = this._getEntityData('solar_flare_current_status');
    const flaresLast = this._getEntityData('solar_flare_last_info');

    let cityName = aurora.attributes.location_name || this.config.city || this.t.loc_default;
    if ((this.hass.language || 'en').substring(0, 2) === 'en' && aurora.attributes.location_name_en) { cityName = aurora.attributes.location_name_en; }
    if (this.config.city) cityName = this.config.city; 

    const kpNum = parseFloat(kp.state);
    let videoUrl = '/api/xras_sw_static/normal.mp4'; 
    let statusName = this.t.norm_status;
    let badgeColor = 'var(--success-color, #4caf50)';
    
    if (!isNaN(kpNum)) {
      if (kpNum >= 9) { videoUrl = '/api/xras_sw_static/g5.mp4'; statusName = this.t.g5_status; badgeColor = 'var(--error-color, #f44336)'; }
      else if (kpNum >= 8) { videoUrl = '/api/xras_sw_static/g4.mp4'; statusName = this.t.g4_status; badgeColor = 'var(--error-color, #f44336)'; }
      else if (kpNum >= 7) { videoUrl = '/api/xras_sw_static/g3.mp4'; statusName = this.t.g3_status; badgeColor = 'var(--warning-color, #ff9800)'; }
      else if (kpNum >= 6) { videoUrl = '/api/xras_sw_static/g2.mp4'; statusName = this.t.g2_status; badgeColor = 'var(--warning-color, #ff9800)'; }
      else if (kpNum >= 5) { videoUrl = '/api/xras_sw_static/g1.mp4'; statusName = this.t.g1_status; badgeColor = 'var(--warning-color, #ff9800)'; }
    }

    return htmlClassic`
      <ha-card>
        <div class="header-container">
          <video id="bg-video" class="bg-video" src=${videoUrl} autoplay loop muted playsinline webkit-playsinline disablePictureInPicture disableRemotePlayback></video>
          <div class="header-overlay">
            <div class="kp-city"><ha-icon icon="mdi:map-marker" style="--mdc-icon-size: 14px; margin-right: 4px;"></ha-icon>${cityName}</div>
            <div class="kp-main">${kp.state} <span style="font-size: 18px;">Kp</span></div>
            <div class="kp-desc"><span class="status-badge" style="background-color: ${badgeColor};"></span>${statusName}</div>
          </div>
        </div>
        <div class="content-body">
          <div class="section">
            <div class="section-title"><ha-icon icon="mdi:aurora"></ha-icon> ${this.t.aurora_title}</div>
            <div class="tile-row"><span class="label">${this.t.ai_label}</span><span class="value">${ai.state} <span class="desc">(${this.t.at_time} ${ai.time})</span></span></div>
            <div class="tile-row"><span class="label">${this.t.prob_label}</span><span class="value">${aurora.state}%</span></div>
          </div>
          <div class="section">
            <div class="section-title"><ha-icon icon="mdi:magnet"></ha-icon> ${this.t.storms_title}</div>
            <div class="tile-row"><span class="label">${this.t.max_today}</span><span class="value">${kpToday.state} <span class="desc">${this._getKpDesc(kpToday.state)}</span></span></div>
            <div class="tile-row"><span class="label">${this.t.tmrw}</span><span class="value">${kpTmrw.state} <span class="desc">${this._getKpDesc(kpTmrw.state)}</span></span></div>
          </div>
          <div class="section">
            <div class="section-title"><ha-icon icon="mdi:white-balance-sunny"></ha-icon> ${this.t.solar_title}</div>
            <div class="tile-row"><span class="label">${this.t.f10_label}</span><span class="value">${f10.state}</span></div>
            <div class="tile-col"><span class="label">${this.t.status_label}</span><span class="value font-normal">${flaresStatus.state}</span></div>
            <div class="tile-col"><span class="label">${this.t.flare_label}</span><span class="value font-normal">${flaresLast.state}</span></div>
          </div>
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return cssClassic`
      ha-card { overflow: hidden; display: flex; flex-direction: column; background: var(--card-background-color); border-radius: var(--ha-card-border-radius, 12px); }
      .header-container { width: 100%; height: 160px; position: relative; display: flex; align-items: flex-end; background-color: #000; overflow: hidden; }
      .bg-video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; pointer-events: none; }
      .header-overlay { width: 100%; position: relative; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.1) 70%, transparent 100%); padding: 16px; color: white; }
      .kp-city { font-size: 12px; font-weight: 500; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; display: flex; align-items: center; }
      .kp-main { font-size: 42px; font-weight: bold; line-height: 1; text-shadow: 1px 1px 4px rgba(0,0,0,0.8); }
      .kp-desc { font-size: 15px; font-weight: 500; margin-top: 6px; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); display: flex; align-items: center; gap: 8px; }
      .status-badge { width: 10px; height: 10px; border-radius: 50%; display: inline-block; box-shadow: 0 0 4px rgba(0,0,0,0.5); }
      .content-body { padding: 16px; display: flex; flex-direction: column; gap: 16px; }
      .section { display: flex; flex-direction: column; gap: 6px; }
      .section-title { font-size: 16px; font-weight: 500; color: var(--primary-text-color); display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
      .section-title ha-icon { color: var(--primary-color); }
      .tile-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--secondary-background-color); border-radius: 8px; }
      .tile-col { display: flex; flex-direction: column; gap: 2px; padding: 10px 14px; background: var(--secondary-background-color); border-radius: 8px; }
      .label { color: var(--secondary-text-color); font-size: 13px; }
      .value { color: var(--primary-text-color); font-size: 14px; font-weight: 500; }
      .font-normal { font-weight: normal; }
      .desc { color: var(--secondary-text-color); font-size: 12px; font-weight: normal; margin-left: 4px; }
    `;
  }
}
customElements.define('space-weather-card-classic', SpaceWeatherCardClassic);

class SWCardClassicEditor extends LitElementClassic {
  setConfig(config) { this._config = config; }
  get t() { const lang = (this.hass?.language || 'en').substring(0, 2); return TRANSLATIONS_CLASSIC[lang] || TRANSLATIONS_CLASSIC['en']; }
  render() {
    if (!this._config) return htmlClassic``;
    return htmlClassic`<div class="card-config"><h3>${this.t.editor.title}</h3><ha-textfield label="${this.t.editor.city_label}" .value=${this._config.city || ""} .configValue=${"city"} @input=${this._valueChanged}></ha-textfield></div>`;
  }
  _valueChanged(ev) {
    if (!this._config || !this.hass) return;
    const target = ev.target;
    if (this[`_${target.configValue}`] === target.value) return;
    this._config = { ...this._config, [target.configValue]: target.value };
    this.dispatchEvent(new Event("config-changed", { bubbles: true, composed: true, detail: { config: this._config } }));
  }
  static get styles() { return cssClassic`.card-config { display: flex; flex-direction: column; gap: 16px; } ha-textfield { width: 100%; }`; }
}
customElements.define("sw-card-classic-editor", SWCardClassicEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'space-weather-card-classic')) {
  const lang = (navigator.language || 'en').substring(0, 2);
  const t = TRANSLATIONS_CLASSIC[lang] || TRANSLATIONS_CLASSIC['en'];
  window.customCards.push({ type: "space-weather-card-classic", name: t.card_name, description: t.card_desc, preview: true });
}
