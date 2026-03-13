"""Координатор данных для интеграции ИКИ РАН: Космическая погода."""
import logging
import asyncio
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, 
    USER_AGENT, 
    URL_JSON_BASE, 
    UPDATE_INTERVAL_MINUTES,
    CITIES
)

_LOGGER = logging.getLogger(__name__)

class XrasDataUpdateCoordinator(DataUpdateCoordinator):
    """Класс для управления скачиванием и парсингом данных."""

    def __init__(self, hass, city_alias):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{city_alias}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.city_alias = city_alias
        self.city_internal_id = CITIES[city_alias]["id"] 
        self.city_name = CITIES[city_alias]["name"]
        self.session = async_get_clientsession(hass)

    async def _fetch(self, url, is_json=True):
        headers = {"User-Agent": USER_AGENT}
        try:
            async with self.session.get(url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                if is_json:
                    return await response.json(content_type=None)
                return await response.text()
        except Exception as err:
            raise UpdateFailed(f"Ошибка при запросе к {url}: {err}") from err

    async def _async_update_data(self):
        try:
            lang = self.hass.config.language
            is_ru = lang.startswith('ru')

            url_ai = f"{URL_JSON_BASE}/ai_{self.city_internal_id}.json"
            url_xray = f"{URL_JSON_BASE}/xray_{self.city_internal_id}.json"
            url_kp_fact = f"{URL_JSON_BASE}/kp_{self.city_internal_id}.json"
            url_kp_forecast = f"{URL_JSON_BASE}/kpf_{self.city_internal_id}.json"

            if is_ru:
                url_aurora_html = f"https://xras.ru/aurora.html/{self.city_alias}/"
                url_flares_html = "https://xras.ru/sun_flares.html"
            else:
                # Используем стандартный путь (он надежнее)
                url_aurora_html = f"https://xras.ru/en/aurora.html/{self.city_alias}/"
                url_flares_html = "https://xras.ru/en/sun_flares.html"

            results = await asyncio.gather(
                self._fetch(url_ai, is_json=True),
                self._fetch(url_xray, is_json=True),
                self._fetch(url_kp_fact, is_json=True),
                self._fetch(url_kp_forecast, is_json=True),
                self._fetch(url_aurora_html, is_json=False),
                self._fetch(url_flares_html, is_json=False),
                return_exceptions=True
            )

            # === БРОНЕБОЙНАЯ ЗАЩИТА ОТ ОШИБОК ===
            # Если какая-то ссылка выдаст 404, мы просто пишем предупреждение и работаем дальше!
            for i, res in enumerate(results):
                if isinstance(res, Exception):
                    _LOGGER.warning(f"Источник {i} временно недоступен: {res}")

            ai_data = results[0] if not isinstance(results[0], Exception) else None
            xray_data = results[1] if not isinstance(results[1], Exception) else None
            kp_fact_data = results[2] if not isinstance(results[2], Exception) else None
            kp_forecast_data = results[3] if not isinstance(results[3], Exception) else None
            aurora_html = results[4] if not isinstance(results[4], Exception) else ""
            flares_html = results[5] if not isinstance(results[5], Exception) else ""

            parsed_data = {}

            if ai_data and "data" in ai_data and len(ai_data["data"]) > 0:
                parsed_data["aurora_index_latest"] = ai_data["data"][0].get("ai", "unknown")
                parsed_data["aurora_time"] = ai_data["data"][0].get("time", "")

            if xray_data and "data" in xray_data and len(xray_data["data"]) > 0:
                parsed_data["solar_xray_latest"] = xray_data["data"][0].get("long", "unknown")

            if kp_fact_data and "data" in kp_fact_data and len(kp_fact_data["data"]) >= 2:
                today_fact = kp_fact_data["data"][0]
                yesterday_fact = kp_fact_data["data"][1]
                
                parsed_data["kp_forecast_today"] = today_fact.get("max_kp", "unknown")
                parsed_data["f10_forecast_today"] = today_fact.get("f10", "unknown")

                latest_kp = "unknown"
                hours = ['h00', 'h03', 'h06', 'h09', 'h12', 'h15', 'h18', 'h21']
                
                for h in hours:
                    val = yesterday_fact.get(h)
                    if val not in ["null", None, "", "-1", "-2"]:
                        latest_kp = str(val).replace('-', '')
                
                for h in hours:
                    val = today_fact.get(h)
                    if val not in ["null", None, "", "-1", "-2"]:
                        latest_kp = str(val).replace('-', '')
                
                parsed_data["kp_current"] = latest_kp

            if kp_forecast_data and "data" in kp_forecast_data:
                msk_tz = timezone(timedelta(hours=3))
                tomorrow_msk = datetime.now(msk_tz) + timedelta(days=1)
                tmrw_str = tomorrow_msk.strftime('%Y-%m-%d')
                
                parsed_data["kp_forecast_tomorrow"] = "unknown"
                for day in kp_forecast_data["data"]:
                    if day.get("time") == tmrw_str:
                        parsed_data["kp_forecast_tomorrow"] = day.get("max_kp", "unknown")
                        break

            parsed_data["aurora_probability_local"] = "unknown"
            soup_aurora = BeautifulSoup(aurora_html, 'html.parser')
            city_search_en = self.city_alias.replace('_', ' ').lower()
            
            for loc in soup_aurora.select('.aurora_location'):
                name_span = loc.select_one('.aurora_location_name')
                if name_span:
                    html_city = name_span.text.lower()
                    if self.city_name.lower() in html_city or city_search_en in html_city:
                        val_span = loc.select_one('.aurora_location_value')
                        if val_span:
                            parsed_data["aurora_probability_local"] = val_span.text.replace(' %', '').strip()
                            break

            parsed_data["solar_flare_current_status"] = "unknown"
            parsed_data["solar_flare_last_info"] = "unknown"
            soup_flares = BeautifulSoup(flares_html, 'html.parser')
            flare_nodes = soup_flares.select('.graph_lastdata_text')
            
            if len(flare_nodes) >= 2:
                parsed_data["solar_flare_current_status"] = flare_nodes[0].text.strip()
                flare_text = flare_nodes[1].text.strip()
                
                match = re.search(r'\b(\d{1,2}):(\d{2})\b', flare_text)
                if match:
                    hours, minutes = int(match.group(1)), int(match.group(2))
                    
                    if is_ru:
                        source_tz = timezone(timedelta(hours=3))
                    else:
                        source_tz = timezone.utc
                        
                    now = dt_util.utcnow()
                    time_source = datetime(now.year, now.month, now.day, hours, minutes, tzinfo=source_tz)
                    time_local = dt_util.as_local(time_source)
                    
                    local_time_str = time_local.strftime('%H:%M')
                    flare_text = flare_text.replace(match.group(0), local_time_str)
                    
                    flare_text = flare_text.replace('МСК', 'Местн.').replace('MSK', 'Local').replace('UTC', 'Local')
                    
                parsed_data["solar_flare_last_info"] = flare_text

            return parsed_data

        except Exception as err:
            _LOGGER.exception("Непредвиденная ошибка в координаторе")
            raise UpdateFailed(f"Ошибка обработки данных: {err}") from err
