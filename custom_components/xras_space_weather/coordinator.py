"""Координатор данных для интеграции ИКИ РАН: Космическая погода."""
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, 
    USER_AGENT, 
    URL_JSON_BASE, 
    URL_HTML_AURORA, 
    URL_HTML_FLARES, 
    UPDATE_INTERVAL_MINUTES,
    CITIES
)

_LOGGER = logging.getLogger(__name__)

class XrasDataUpdateCoordinator(DataUpdateCoordinator):
    """Класс для управления скачиванием и парсингом данных."""

    def __init__(self, hass, city_alias):
        """Инициализация координатора."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{city_alias}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.city_alias = city_alias
        self.city_internal_id = CITIES[city_alias]["id"] # Правильный ключ для RAL5 и т.д.
        self.city_name = CITIES[city_alias]["name"]
        self.session = async_get_clientsession(hass)

    async def _fetch(self, url, is_json=True):
        """Вспомогательная функция для скачивания данных."""
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
        """Главная функция: скачивает всё и парсит данные."""
        try:
            # 1. Формируем ссылки с правильным внутренним ID
            url_ai = f"{URL_JSON_BASE}/ai_{self.city_internal_id}.json"
            url_xray = f"{URL_JSON_BASE}/xray_{self.city_internal_id}.json"
            url_kp_fact = f"{URL_JSON_BASE}/kp_{self.city_internal_id}.json"
            url_kp_forecast = f"{URL_JSON_BASE}/kpf_{self.city_internal_id}.json"
            url_aurora_html = f"{URL_HTML_AURORA}/{self.city_alias}/"

            # 2. Скачиваем всё параллельно
            results = await asyncio.gather(
                self._fetch(url_ai, is_json=True),
                self._fetch(url_xray, is_json=True),
                self._fetch(url_kp_fact, is_json=True),
                self._fetch(url_kp_forecast, is_json=True),
                self._fetch(url_aurora_html, is_json=False),
                self._fetch(URL_HTML_FLARES, is_json=False),
                return_exceptions=True
            )

            for res in results:
                if isinstance(res, Exception):
                    raise UpdateFailed(f"Ошибка параллельного запроса: {res}")

            ai_data, xray_data, kp_fact_data, kp_forecast_data, aurora_html, flares_html = results

            parsed_data = {}

            # --- Индекс сияний (AI) ---
            if ai_data and "data" in ai_data and len(ai_data["data"]) > 0:
                parsed_data["aurora_index"] = ai_data["data"][0].get("ai", "unknown")
                parsed_data["aurora_time"] = ai_data["data"][0].get("time", "")

            # --- Рентгеновское излучение (X-Ray) ---
            if xray_data and "data" in xray_data and len(xray_data["data"]) > 0:
                parsed_data["solar_xray"] = xray_data["data"][0].get("long", "unknown")

            # --- ФАКТИЧЕСКИЕ ДАННЫЕ И ТЕКУЩИЙ KP ---
            if kp_fact_data and "data" in kp_fact_data and len(kp_fact_data["data"]) >= 2:
                today_fact = kp_fact_data["data"][0]
                yesterday_fact = kp_fact_data["data"][1]
                
                parsed_data["kp_max_today"] = today_fact.get("max_kp", "unknown")
                parsed_data["f10_today"] = today_fact.get("f10", "unknown")

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

            # --- ПРОГНОЗ НА ЗАВТРА ---
            if kp_forecast_data and "data" in kp_forecast_data:
                msk_tz = timezone(timedelta(hours=3))
                tomorrow_msk = datetime.now(msk_tz) + timedelta(days=1)
                tmrw_str = tomorrow_msk.strftime('%Y-%m-%d')
                
                parsed_data["kp_forecast_tomorrow"] = "unknown"
                for day in kp_forecast_data["data"]:
                    if day.get("time") == tmrw_str:
                        parsed_data["kp_forecast_tomorrow"] = day.get("max_kp", "unknown")
                        break

            # --- ПАРСИНГ HTML: Вероятность сияний ---
            parsed_data["aurora_probability"] = "unknown"
            soup_aurora = BeautifulSoup(aurora_html, 'html.parser')
            for loc in soup_aurora.select('.aurora_location'):
                name_span = loc.select_one('.aurora_location_name')
                if name_span and self.city_name in name_span.text:
                    val_span = loc.select_one('.aurora_location_value')
                    if val_span:
                        parsed_data["aurora_probability"] = val_span.text.replace(' %', '').strip()
                        break

            # --- ПАРСИНГ HTML: Вспышки на солнце ---
            parsed_data["flare_status"] = "unknown"
            parsed_data["flare_info"] = "unknown"
            soup_flares = BeautifulSoup(flares_html, 'html.parser')
            flare_nodes = soup_flares.select('.graph_lastdata_text')
            if len(flare_nodes) >= 2:
                parsed_data["flare_status"] = flare_nodes[0].text.strip()
                parsed_data["flare_info"] = flare_nodes[1].text.strip()

            return parsed_data

        except Exception as err:
            _LOGGER.exception("Непредвиденная ошибка в координаторе")
            raise UpdateFailed(f"Ошибка обработки данных: {err}") from err
