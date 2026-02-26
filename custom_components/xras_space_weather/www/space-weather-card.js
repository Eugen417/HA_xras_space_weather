class SpaceWeatherCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._isInitialized = false;
  }

  setConfig(config) {
    this.config = config || {};
  }

  // Вызывается браузером, когда карточка реально появляется на экране
  connectedCallback() {
    if (this.videoEl) {
      // Принудительный старт видео при открытии дашборда (Лечит зависание в Chrome/App)
      this.videoEl.muted = true;
      this.videoEl.play().catch(() => {});
    }
  }

  set hass(hass) {
    this._hass = hass;
    
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
            <div class="section-title">🌌 Полярные сияния</div>
            <div class="row-inline"><span class="label">Индекс активности:</span><span class="value" id="ai-val">--</span></div>
            <div class="row-inline"><span class="label">Вероятность в локации:</span><span class="value" id="aurora-val">--</span></div>
          </div>
          <div class="section">
            <div class="section-title">🧲 Магнитные бури</div>
            <div class="row-inline"><span class="label">Максимум за сегодня:</span><span class="value" id="kp-today-val">--</span></div>
            <div class="row-inline"><span class="label">Ожидается завтра:</span><span class="value" id="kp-tmrw-val">--</span></div>
          </div>
          <div class="section">
            <div class="section-title">☀️ Солнечная активность</div>
            <div class="row-inline"><span class="label">Индекс излучения (F10.7):</span><span class="value" id="f10-val">--</span></div>
            <div class="row-block"><span class="label">Статус:</span><span class="value" style="font-weight: normal;" id="flare-status-val">--</span></div>
            <div class="row-block"><span class="label">Последняя вспышка:</span><span class="value" style="font-weight: normal;" id="flare-last-val">--</span></div>
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

    const getEntityData = (suffix) => {
      const eid = this._getEntity(suffix);
      if (eid && this._hass.states[eid]) {
        const stateObj = this._hass.states[eid];
        let timeStr = '--:--';
        if (stateObj.last_updated) {
          try {
            const d = new Date(stateObj.last_updated.replace(' ', 'T'));
            if (!isNaN(d.getTime())) timeStr = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
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

    const cityName = aurora.attributes.location_name || aurora.attributes.city || this.config.city || 'Локация';
    const kpNum = parseFloat(kp.state);
    
    let videoUrl = this._currentVideoUrl || '/xras_sw_static/normal.mp4'; 
    let statusName = this.statusNameEl.innerHTML !== '--' ? this.statusNameEl.innerHTML : 'Норма (Без бурь)';
    
    // ЗАЩИТА ОТ "МОРГАНИЯ" СЕНСОРОВ
    // Обновляем ссылку на видео ТОЛЬКО если пришло реальное число
    if (!isNaN(kpNum)) {
      if (kpNum >= 9) { videoUrl = '/xras_sw_static/g5.mp4'; statusName = 'G5 (Экстремально)'; }
      else if (kpNum >= 8) { videoUrl = '/xras_sw_static/g4.mp4'; statusName = 'G4 (Очень сильно)'; }
      else if (kpNum >= 7) { videoUrl = '/xras_sw_static/g3.mp4'; statusName = 'G3 (Сильная буря)'; }
      else if (kpNum >= 6) { videoUrl = '/xras_sw_static/g2.mp4'; statusName = 'G2 (Умеренная буря)'; }
      else if (kpNum >= 5) { videoUrl = '/xras_sw_static/g1.mp4'; statusName = 'G1 (Слабая буря)'; }
      else { videoUrl = '/xras_sw_static/normal.mp4'; statusName = 'Норма (Без бурь)'; }
    }

    const getKpDesc = (val) => {
      const n = parseFloat(val);
      if (isNaN(n)) return '';
      if (n < 5) return '(Норма)';
      return `(Буря G${Math.floor(n - 4)})`;
    };

    // ОБНОВЛЕНИЕ ВИДЕО (Только если реально сменился уровень бури)
    if (this._currentVideoUrl !== videoUrl) {
      this.videoEl.src = videoUrl;
      this._currentVideoUrl = videoUrl;
      this.videoEl.muted = true;
      this.videoEl.play().catch(() => {});
    }
    
    // Если видео почему-то встало на паузу (политика браузера), пинаем его снова
    if (this.videoEl.paused) {
        this.videoEl.play().catch(() => {});
    }

    this.cityNameEl.innerHTML = cityName;
    this.kpValEl.innerHTML = kp.state;
    this.statusNameEl.innerHTML = statusName;
    
    this.aiValEl.innerHTML = `${ai.state} AI <span class="desc">(на ${ai.time})</span>`;
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
  window.customCards.push({
    type: "space-weather-card",
    name: "Space Weather",
    description: "Анимации уровней угрозы и полная текстовая сводка ИКИ РАН",
    preview: true
  });
}
