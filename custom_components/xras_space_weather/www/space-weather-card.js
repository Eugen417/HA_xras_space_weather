class SpaceWeatherCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this.config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.card) {
      this.card = document.createElement('ha-card');
      this.card.style.overflow = 'hidden'; 
      this.content = document.createElement('div');
      
      const style = document.createElement('style');
      style.textContent = `
        .header-container {
          width: 100%;
          height: 150px;
          position: relative;
          display: flex;
          align-items: flex-end;
          background-color: #000;
          overflow: hidden;
        }
        .bg-video {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          z-index: 0;
        }
        .header-overlay {
          width: 100%;
          position: relative;
          z-index: 1;
          background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.1) 70%, transparent 100%);
          padding: 12px 16px;
          color: white;
        }
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
      
      this.card.appendChild(style);
      this.card.appendChild(this.content);
      this.shadowRoot.appendChild(this.card);
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
    if (!this._hass || !this.content) return;

    const getEntityData = (suffix) => {
      const eid = this._getEntity(suffix);
      if (eid && this._hass.states[eid]) {
        const stateObj = this._hass.states[eid];
        let timeStr = '--:--';
        if (stateObj.last_updated) {
          try {
            // Safari fix: замена пробела на T для корректного парсинга даты
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
    
    let videoUrl = '/xras_sw_static/normal.mp4'; 
    let statusName = 'Норма (Без бурь)';
    
    if (!isNaN(kpNum)) {
      if (kpNum >= 9) { videoUrl = '/xras_sw_static/g5.mp4'; statusName = 'G5 (Экстремально)'; }
      else if (kpNum >= 8) { videoUrl = '/xras_sw_static/g4.mp4'; statusName = 'G4 (Очень сильно)'; }
      else if (kpNum >= 7) { videoUrl = '/xras_sw_static/g3.mp4'; statusName = 'G3 (Сильная буря)'; }
      else if (kpNum >= 6) { videoUrl = '/xras_sw_static/g2.mp4'; statusName = 'G2 (Умеренная буря)'; }
      else if (kpNum >= 5) { videoUrl = '/xras_sw_static/g1.mp4'; statusName = 'G1 (Слабая буря)'; }
    }

    const getKpDesc = (val) => {
      const n = parseFloat(val);
      if (isNaN(n)) return '';
      if (n < 5) return '(Норма)';
      return `(Буря G${Math.floor(n - 4)})`;
    };

    this.content.innerHTML = `
      <div class="header-container">
        <video class="bg-video" src="${videoUrl}" autoplay loop muted playsinline webkit-playsinline></video>
        
        <div class="header-overlay">
          <div class="kp-city"><ha-icon icon="mdi:map-marker" style="--mdc-icon-size: 12px; margin-right: 4px;"></ha-icon>${cityName}</div>
          <div class="kp-main">${kp.state} <span>Kp</span></div>
          <div class="kp-desc">${statusName}</div>
        </div>
      </div>
      
      <div class="content-body">
        <div class="section">
          <div class="section-title">🌌 Полярные сияния</div>
          <div class="row-inline">
            <span class="label">Индекс активности:</span>
            <span class="value">${ai.state} AI <span class="desc">(на ${ai.time})</span></span>
          </div>
          <div class="row-inline">
            <span class="label">Вероятность в локации:</span>
            <span class="value">${aurora.state}%</span>
          </div>
        </div>

        <div class="section">
          <div class="section-title">🧲 Магнитные бури</div>
          <div class="row-inline">
            <span class="label">Максимум за сегодня:</span>
            <span class="value">${kpToday.state} Kp <span class="desc">${getKpDesc(kpToday.state)}</span></span>
          </div>
          <div class="row-inline">
            <span class="label">Ожидается завтра:</span>
            <span class="value">${kpTmrw.state} Kp <span class="desc">${getKpDesc(kpTmrw.state)}</span></span>
          </div>
        </div>

        <div class="section">
          <div class="section-title">☀️ Солнечная активность</div>
          <div class="row-inline">
            <span class="label">Индекс излучения (F10.7):</span>
            <span class="value">${f10.state}</span>
          </div>
          <div class="row-block">
            <span class="label">Статус:</span>
            <span class="value" style="font-weight: normal;">${flaresStatus.state}</span>
          </div>
          <div class="row-block">
            <span class="label">Последняя вспышка:</span>
            <span class="value" style="font-weight: normal;">${flaresLast.state}</span>
          </div>
        </div>
      </div>
    `;
  }

  getCardSize() { return 8; }
}

// 🛡 НАДЕЖНАЯ ПРОВЕРКА РЕГИСТРАЦИИ (Safari / iOS Fix)
try {
  if (!customElements.get('space-weather-card')) {
    customElements.define('space-weather-card', SpaceWeatherCard);
  }
} catch (e) {
  console.warn('⚠️ Ошибка регистрации space-weather-card:', e);
}

// Добавляем в визуальный редактор карточек
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'space-weather-card')) {
  window.customCards.push({
    type: "space-weather-card",
    name: "Space Weather",
    description: "Анимации уровней угрозы (Видео-фон) и полная текстовая сводка ИКИ РАН",
    preview: true
  });
}
