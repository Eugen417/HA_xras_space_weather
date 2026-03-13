const TRANSLATIONS = {
  en: {
    aurora_title: "🌌 Auroras",
    ai_label: "Activity Index:",
    prob_label: "Probability at location:",
    storms_title: "🧲 Magnetic Storms",
    max_today: "Maximum today:",
    tmrw: "Expected tomorrow:",
    solar_title: "☀️ Solar Activity",
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
    card_name: "Space Weather",
    card_desc: "Animations of threat levels and full summary from IKI RAN"
  },
  ru: {
    aurora_title: "🌌 Полярные сияния",
    ai_label: "Индекс активности:",
    prob_label: "Вероятность в локации:",
    storms_title: "🧲 Магнитные бури",
    max_today: "Максимум за сегодня:",
    tmrw: "Ожидается завтра:",
    solar_title: "☀️ Солнечная активность",
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
    card_name: "Космическая погода",
    card_desc: "Анимации уровней угрозы и полная текстовая сводка ИКИ РАН"
  }
};

class SpaceWeatherCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._isInitialized = false;
  }

  setConfig(config) {
    this.config = config || {};
  }

  connectedCallback() {
    if (this.videoEl) {
      this.videoEl.muted = true;
      this.videoEl.defaultMuted = true;
      this.videoEl.setAttribute('playsinline', '');
      this.videoEl.setAttribute('webkit-playsinline', '');
      this.videoEl.play().catch(() => {});
    }
  }

  set hass(hass) {
    this._hass = hass;
    
    const langCode = (hass.language || 'en').substring(0, 2);
    this.t = TRANSLATIONS[langCode] || TRANSLATIONS['en'];
    
    if (!this._isInitialized) {
      this.card = document.createElement('ha-card');
      this.card.style.overflow = 'hidden'; 
      this.content = document.createElement('div');
      
      const style = document.createElement('style');
      style.textContent = `
        .header-container { width: 100%; height: 150px; position: relative; display: flex; align-items: flex-end; background-color: #000; overflow: hidden; }
        .bg-video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; pointer-events: none; }
        .header-overlay { width: 100%; position: relative; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.1) 70%, transparent 100%); padding: 12px 16px; color: white; }
        .kp-city { font-size: 11px; font-weight: 500; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; display: flex; align-items: center; }
        .kp-main { font-size: 32px; font-weight: bold; line-height: 1; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
        .kp-main span { font-size: 16px; font-weight: normal; opacity: 0.9; }
        .kp-desc { font-size: 14px; font-weight: 500; margin-top: 2px; opacity: 0.9; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
        .content-body { padding: 16px; }
        .section { margin-bottom: 20px; }
        .section-title { font-size: 16px; font-weight: 500; margin-bottom: 12px; color: var(--primary-text-color); display: flex; align-items: center; gap: 8px; }
        .row-inline { display: flex; flex-direction: row; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; padding-left: 12px; border-left: 2px solid var(--primary-color); align-items: baseline; }
        .row-block { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; padding-left: 12px; border-left: 2px solid var(--primary-color); }
        .label { color: var(--secondary-text-color); font-size: 14px; }
        .value { color: var(--primary-text-color); font-size: 14px; font-weight: 500; }
        .desc { color: var(--secondary-text-color); font-size: 13px; font-weight: normal; }
      `;
      
      this.content.innerHTML = `
        <div class="header-container">
          <video id="bg-video" class="bg-video" autoplay loop muted playsinline webkit-playsinline disablePictureInPicture disableRemotePlayback></video>
          <div class="header-overlay">
            <div class="kp-city"><ha-icon icon="mdi:map-marker" style="--mdc-icon-size: 12px; margin-right: 4px;"></ha-icon><span id="city-name">--</span></div>
            <div class="kp-main"><span id="kp-val">--</span> <span>Kp</span></div>
            <div class="kp-desc" id="status-name">--</div>
          </div>
        </div>
        <div class="content-body">
          <div class="section">
            <div class="section-title">${this.t.aurora_title}</div>
            <div class="row-inline"><span class="label">${this.t.ai_label}</span><span class="value" id="ai-val">--</span></div>
            <div class="row-inline"><span class="label">${this.t.prob_label}</span><span class="value" id="aurora-val">--</span></div>
          </div>
          <div class="section">
            <div class="section-title">${this.t.storms_title}</div>
            <div class="row-inline"><span class="label">${this.t.max_today}</span><span class="value" id="kp-today-val">--</span></div>
            <div class="row-inline"><span class="label">${this.t.tmrw}</span><span class="value" id="kp-tmrw-val">--</span></div>
          </div>
          <div class="section">
            <div class="section-title">${this.t.solar_title}</div>
            <div class="row-inline"><span class="label">${this.t.f10_label}</span><span class="value" id="f10-val">--</span></div>
            <div class="row-block"><span class="label">${this.t.status_label}</span><span class="value" style="font-weight: normal;" id="flare-status-val">--</span></div>
            <div class="row-block"><span class="label">${this.t.flare_label}</span><span class="value" style="font-weight: normal;" id="flare-last-val">--</span></div>
          </div>
        </div>
      `;

      this.card.appendChild(style);
      this.card.appendChild(this.content);
      this.shadowRoot.appendChild(this.card);
      
      this.videoEl = this.content.querySelector('#bg-video');
      this.cityNameEl = this.content.querySelector('#city-name');
      this.kpValEl = this.content.querySelector('#kp-val');
      this.statusNameEl = this.content.querySelector('#status-name');
      this.aiValEl = this.content.querySelector('#ai-val');
      this.auroraValEl = this.content.querySelector('#aurora-val');
      this.kpTodayValEl = this.content.querySelector('#kp-today-val');
      this.kpTmrwValEl = this.content.querySelector('#kp-tmrw-val');
      this.f10ValEl = this.content.querySelector('#f10-val');
      this.flareStatusValEl = this.content.querySelector('#flare-status-val');
      this.flareLastValEl = this.content.querySelector('#flare-last-val');

      this._currentVideoUrl = '';
      this._isInitialized = true;
    }
    
    this.render();
  }

  _getEntity(suffix) {
    if (this.config['entity_' + suffix]) return this.config['entity_' + suffix];
    for (let eid in this._hass.states) {
      if (eid.includes(suffix)) return eid;
    }
    return null;
  }

  render() {
    if (!this._hass || !this._isInitialized) return;

    const langCode = (this._hass.language || 'en').substring(0, 2);

    const getEntityData = (suffix) => {
      const eid = this._getEntity(suffix);
      if (eid && this._hass.states[eid]) {
        const stateObj = this._hass.states[eid];
        let timeStr = '--:--';
        if (stateObj.last_updated) {
          try {
            const d = new Date(stateObj.last_updated.replace(' ', 'T'));
            if (!isNaN(d.getTime())) timeStr = d.toLocaleTimeString(this._hass.language || 'ru-RU', { hour: '2-digit', minute: '2-digit' });
          } catch(e) {}
        }
        return { state: String(stateObj.state), time: timeStr, attributes: stateObj.attributes || {} };
      }
      return { state: '--', time: '--:--', attributes: {} };
    };

    const ai = getEntityData('aurora_index_latest');
    const aurora = getEntityData('aurora_probability_local');
    const kp = getEntityData('kp_current');
    const kpToday = getEntityData('kp_forecast_today');
    const kpTmrw = getEntityData('kp_forecast_tomorrow');
    const f10 = getEntityData('f10_forecast_today');
    const flaresStatus = getEntityData('solar_flare_current_status');
    const flaresLast = getEntityData('solar_flare_last_info');

    let cityName = aurora.attributes.location_name || this.config.city || this.t.loc_default;
    if (langCode === 'en' && aurora.attributes.location_name_en) {
        cityName = aurora.attributes.location_name_en;
    }

    const kpNum = parseFloat(kp.state);
    
    let videoUrl = '/api/xras_sw_static/normal.mp4'; 
    let statusName = this.statusNameEl.innerHTML !== '--' ? this.statusNameEl.innerHTML : this.t.norm_status;
    
    if (!isNaN(kpNum)) {
      if (kpNum >= 9) { videoUrl = '/api/xras_sw_static/g5.mp4'; statusName = this.t.g5_status; }
      else if (kpNum >= 8) { videoUrl = '/api/xras_sw_static/g4.mp4'; statusName = this.t.g4_status; }
      else if (kpNum >= 7) { videoUrl = '/api/xras_sw_static/g3.mp4'; statusName = this.t.g3_status; }
      else if (kpNum >= 6) { videoUrl = '/api/xras_sw_static/g2.mp4'; statusName = this.t.g2_status; }
      else if (kpNum >= 5) { videoUrl = '/api/xras_sw_static/g1.mp4'; statusName = this.t.g1_status; }
      else { videoUrl = '/api/xras_sw_static/normal.mp4'; statusName = this.t.norm_status; }
    }

    const getKpDesc = (val) => {
      const n = parseFloat(val);
      if (isNaN(n)) return '';
      if (n < 5) return this.t.desc_norm;
      return `(${this.t.desc_storm}${Math.floor(n - 4)})`;
    };

    if (this._currentVideoUrl !== videoUrl) {
      this._currentVideoUrl = videoUrl; 
      
      const cacheBustUrl = videoUrl + "?v=" + Date.now();
      this.videoEl.src = cacheBustUrl;
      
      this.videoEl.muted = true;
      this.videoEl.defaultMuted = true; 
      
      this.videoEl.setAttribute('playsinline', '');
      this.videoEl.setAttribute('webkit-playsinline', '');
      this.videoEl.setAttribute('autoplay', '');
      
      this.videoEl.load(); 
      
      const playPromise = this.videoEl.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          setTimeout(() => {
            this.videoEl.play().catch(() => {});
          }, 500);
        });
      }
    }
    
    if (this.videoEl.paused) {
        this.videoEl.play().catch(() => {});
    }

    this.cityNameEl.innerHTML = cityName;
    this.kpValEl.innerHTML = kp.state;
    this.statusNameEl.innerHTML = statusName;
    
    this.aiValEl.innerHTML = `${ai.state} AI <span class="desc">(${this.t.at_time} ${ai.time})</span>`;
    this.auroraValEl.innerHTML = `${aurora.state}%`;
    
    this.kpTodayValEl.innerHTML = `${kpToday.state} Kp <span class="desc">${getKpDesc(kpToday.state)}</span>`;
    this.kpTmrwValEl.innerHTML = `${kpTmrw.state} Kp <span class="desc">${getKpDesc(kpTmrw.state)}</span>`;
    
    this.f10ValEl.innerHTML = f10.state;
    this.flareStatusValEl.innerHTML = flaresStatus.state;
    this.flareLastValEl.innerHTML = flaresLast.state;
  }

  getCardSize() { return 8; }
}

customElements.define('space-weather-card', SpaceWeatherCard);

window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'space-weather-card')) {
  const lang = (navigator.language || 'en').substring(0, 2);
  const t = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  
  window.customCards.push({
    type: "space-weather-card",
    name: t.card_name,
    description: t.card_desc,
    preview: true
  });
}
