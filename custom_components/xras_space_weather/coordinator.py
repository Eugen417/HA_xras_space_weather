"""Координатор данных для интеграции ИКИ РАН: Космическая погода.v3.0.2"""
import logging
import asyncio
import re
import json
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

URL_NOAA_STORM_PROB = "https://services.swpc.noaa.gov/json/3-day-forecast.json"

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
                if response.status != 200:
                    return None
                if is_json:
                    text = await response.text()
                    if not text.strip():
                        return None
                    return await response.json(content_type=None)
                return await response.text()
        except Exception as err:
            _LOGGER.debug(f"Ошибка при запросе к {url}: {err}")
            return None

    def _get_kp_status_text(self, kp_val, is_ru):
        try:
            val = float(kp_val)
            if val < 4:
                return "Магнитосфера спокойная" if is_ru else "Magnetosphere is quiet"
            elif val < 5:
                return "Магнитосфера слабо возмущенная" if is_ru else "Magnetosphere is unsettled"
            elif val < 6:
                return "Слабая магнитная буря (G1)" if is_ru else "Minor geomagnetic storm (G1)"
            elif val < 7:
                return "Умеренная магнитная буря (G2)" if is_ru else "Moderate geomagnetic storm (G2)"
            elif val < 8:
                return "Сильная магнитная буря (G3)" if is_ru else "Strong geomagnetic storm (G3)"
            elif val < 9:
                return "Очень сильная магнитная буря (G4)" if is_ru else "Severe geomagnetic storm (G4)"
            else:
                return "Экстремальная магнитная буря (G5)" if is_ru else "Extreme geomagnetic storm (G5)"
        except Exception:
            return "Неизвестно" if is_ru else "Unknown"

    def _is_valid_value(self, val):
        """Проверяет, является ли значение реальным числом больше нуля (отсекает -9999.00 и null)"""
        if val in (None, "null", "", "unknown"):
            return False
        try:
            num = float(val)
            # Если это отрицательное значение вроде -9999 или -99.9, мы его бракуем.
            # Поле Bz может быть отрицательным, поэтому для него мы эту функцию использовать не будем,
            # но для скорости (v), температуры (t), плотности (n) и поля Bt она идеальна.
            if num <= -100: 
                return False
            return True
        except ValueError:
            return False

    def _is_valid_bz(self, val):
        """Специальная проверка для Bz (может быть отрицательным, но не -9999)"""
        if val in (None, "null", "", "unknown"):
            return False
        try:
            num = float(val)
            if num <= -100: # Отсекаем технические -9999
                return False
            return True
        except ValueError:
            return False

    async def _async_update_data(self):
        try:
            lang = self.hass.config.language
            is_ru = lang.startswith('ru')

            url_ai = f"{URL_JSON_BASE}/ai_{self.city_internal_id}.json"
            url_xray = f"{URL_JSON_BASE}/xray_{self.city_internal_id}.json"
            url_kp_3d = f"{URL_JSON_BASE}/kp_{self.city_internal_id}.json"
            url_kp_month = f"{URL_JSON_BASE}/kpm_{self.city_internal_id}.json"
            url_kp_forecast = f"{URL_JSON_BASE}/kpfl_{self.city_internal_id}.json"
            url_kpf_3d = f"{URL_JSON_BASE}/kpf_{self.city_internal_id}.json"
            
            url_swv = f"{URL_JSON_BASE}/swv_{self.city_internal_id}.json" 
            url_swbt = f"{URL_JSON_BASE}/swbt_{self.city_internal_id}.json" 
            url_swbz = f"{URL_JSON_BASE}/swbz_{self.city_internal_id}.json" 
            url_swt = f"{URL_JSON_BASE}/swt_{self.city_internal_id}.json" 
            url_swn = f"{URL_JSON_BASE}/swn_{self.city_internal_id}.json" 

            url_aurora_html = f"https://xras.ru/{'aurora.html/' if is_ru else 'en/aurora.html/'}{self.city_alias}/"
            url_main_html = f"https://xras.ru/{'' if is_ru else 'en/'}"
            url_active_areas = f"https://xras.ru/{'active_areas.html' if is_ru else 'en/active_areas.html'}"

            tasks = {
                "ai": self._fetch(url_ai, is_json=True),
                "xray": self._fetch(url_xray, is_json=True),
                "kp_3d": self._fetch(url_kp_3d, is_json=True),
                "kp_month": self._fetch(url_kp_month, is_json=True),
                "kp_forecast": self._fetch(url_kp_forecast, is_json=True),
                "aurora_html": self._fetch(url_aurora_html, is_json=False),
                "main_html": self._fetch(url_main_html, is_json=False),
                "swv": self._fetch(url_swv, is_json=True),
                "swbt": self._fetch(url_swbt, is_json=True),
                "swbz": self._fetch(url_swbz, is_json=True),
                "swt": self._fetch(url_swt, is_json=True),
                "swn": self._fetch(url_swn, is_json=True),
                "kpf_3d": self._fetch(url_kpf_3d, is_json=True),
                "active_areas": self._fetch(url_active_areas, is_json=False),
                "noaa_prob": self._fetch(URL_NOAA_STORM_PROB, is_json=True)
            }
            
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            res_dict = dict(zip(tasks.keys(), results))

            def get_res(key):
                res = res_dict[key]
                return res if not isinstance(res, Exception) else None

            ai_data = get_res("ai")
            xray_data = get_res("xray")
            kp_3d_data = get_res("kp_3d")
            kp_month_data = get_res("kp_month")
            kp_forecast_data = get_res("kp_forecast")
            aurora_html = get_res("aurora_html")
            main_html = get_res("main_html")
            active_areas_html = get_res("active_areas")
            kpf_3d_data = get_res("kpf_3d")
            noaa_prob_raw = get_res("noaa_prob")

            swv_data = get_res("swv")
            swbt_data = get_res("swbt")
            swbz_data = get_res("swbz")
            swt_data = get_res("swt")
            swn_data = get_res("swn")

            parsed_data = {}

            # 1. АВРОРА И РЕНТГЕН
            parsed_data["aurora_index_latest"] = "unknown"
            if ai_data and not ai_data.get("error") and "data" in ai_data and len(ai_data["data"]) > 0:
                latest_ai_item = ai_data["data"][0]
                parsed_data["aurora_index_latest"] = latest_ai_item.get("n_ai", latest_ai_item.get("ai", "unknown"))
                parsed_data["aurora_time"] = latest_ai_item.get("time", "")
                parsed_data["aurora_history"] = ai_data["data"][:48]

            parsed_data["xray_current"] = "unknown"
            parsed_data["solar_xray_latest"] = "unknown"
            if xray_data and not xray_data.get("error") and "data" in xray_data and len(xray_data["data"]) > 0:
                xray_val = xray_data["data"][0].get("long", "unknown")
                parsed_data["xray_current"] = xray_val
                parsed_data["solar_xray_latest"] = xray_val
                parsed_data["xray_history"] = xray_data["data"][:60]

            # 2. KP ИНДЕКС
            msk_tz = timezone(timedelta(hours=3))
            now_msk = datetime.now(msk_tz)
            today_str = now_msk.strftime('%Y-%m-%d')
            yesterday_str = (now_msk - timedelta(days=1)).strftime('%Y-%m-%d')
            tmrw_str = (now_msk + timedelta(days=1)).strftime('%Y-%m-%d')

            latest_kp = "unknown"
            parsed_data["kp_forecast_today"] = "unknown"
            parsed_data["f10_forecast_today"] = "unknown"
            
            if kp_3d_data and not kp_3d_data.get("error") and "data" in kp_3d_data:
                parsed_data["kp_3d_array"] = kp_3d_data["data"]
                for day in kp_3d_data["data"]:
                    if day.get("time") == today_str:
                        parsed_data["kp_forecast_today"] = day.get("max_kp", "unknown")
                        parsed_data["f10_forecast_today"] = day.get("f10", "unknown")
                        latest_kp = day.get("max_kp", "unknown")
                        
                        hours = ['h00', 'h03', 'h06', 'h09', 'h12', 'h15', 'h18', 'h21']
                        for h in hours:
                            val = day.get(h)
                            if val not in ["null", None, "", "-1", "-2"]:
                                latest_kp = str(val).replace('-', '')

            parsed_data["kp_current"] = latest_kp
            parsed_data["kp_status_text"] = self._get_kp_status_text(latest_kp, is_ru)

            if kp_month_data and not kp_month_data.get("error") and "data" in kp_month_data:
                parsed_data["kp_month_array"] = kp_month_data["data"]

            parsed_data["kp_forecast_tomorrow"] = "unknown"
            parsed_data["forecast27_max_kp"] = "unknown"
            if kp_forecast_data and not kp_forecast_data.get("error") and "data" in kp_forecast_data:
                parsed_data["forecast27_array"] = kp_forecast_data["data"]
                for day in kp_forecast_data["data"]:
                    if day.get("time") == tmrw_str:
                        parsed_data["kp_forecast_tomorrow"] = day.get("max_kp", "unknown")
                    elif day.get("time") == today_str and parsed_data["kp_forecast_today"] == "unknown":
                         parsed_data["kp_forecast_today"] = day.get("max_kp", "unknown")
                         parsed_data["f10_forecast_today"] = day.get("f10", "unknown")

                try:
                    kps = [float(x["max_kp"]) for x in kp_forecast_data["data"] if x.get("max_kp") not in (None, "null", "unknown")]
                    parsed_data["forecast27_max_kp"] = str(max(kps)) if kps else "unknown"
                except Exception:
                    pass

            # 3. АВРОРА ВЕРОЯТНОСТЬ
            parsed_data["aurora_probability_local"] = "unknown"
            if aurora_html:
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

            # 4. СОЛНЕЧНЫЕ ВСПЫШКИ
            parsed_data["solar_flare_current_status"] = "В настоящий момент не наблюдаются" if is_ru else "None currently observed"
            parsed_data["solar_flare_last_info"] = "Нет данных" if is_ru else "No data"
            parsed_data["flare_summary"] = "0 вспышек за 24 часа | C — 0 | M — 0 | X — 0"
            parsed_data["flare_index"] = "—"
            parsed_data["flares_list"] = []

            if main_html:
                soup_main = BeautifulSoup(main_html, 'html.parser')
                index_span = soup_main.select_one('.home-tile--flare .home-tile__badge')
                if index_span:
                    parsed_data["flare_index"] = index_span.text.strip()
                
                meta_spans = soup_main.select('.home-tile--flare .home-tile__meta-line')
                if len(meta_spans) >= 2:
                    parsed_data["flare_summary"] = f"{meta_spans[0].text.strip()} {meta_spans[1].text.strip()}"
                
                title_span = soup_main.select_one('.home-tile--flare .home-tile__title')
                if title_span:
                    parsed_data["solar_flare_current_status"] = title_span.text.strip()
                
                flares_parsed = []
                for row in soup_main.select('.home-tile__flare-row'):
                    cls_elem = row.select_one('.home-tile__flare-class')
                    time_elem = row.select_one('.home-tile__flare-time')
                    area_elem = row.select_one('.home-tile__flare-area')
                    if cls_elem and time_elem and area_elem:
                        cls_val = cls_elem.text.strip()
                        time_val = time_elem.text.replace('\xa0', ' ').strip()
                        reg_val = area_elem.text.replace('—', '-').strip()
                        flares_parsed.append({"cls": cls_val, "time": time_val, "reg": reg_val})
                
                if flares_parsed:
                    last_f = flares_parsed[0]
                    parsed_data["solar_flare_last_info"] = f"Последняя вспышка: класс {last_f['cls']}, время {last_f['time']}, обл. {last_f['reg']}"
                
                parsed_data["flares_list"] = flares_parsed

            # 5. СОЛНЕЧНЫЙ ВЕТЕР (НАДЕЖНЫЙ ПАРСИНГ С ЖЕСТКОЙ ФИЛЬТРАЦИЕЙ -9999.00)
            parsed_data["swv_current"] = "unknown"
            parsed_data["sw_bt"] = "0.0"
            parsed_data["sw_bz"] = "0.0"
            parsed_data["sw_density"] = "0.0"
            parsed_data["sw_temp"] = "0"
            
            parsed_data["swv_history"] = []
            parsed_data["swbt_history"] = []
            parsed_data["swbz_history"] = []
            parsed_data["swt_history"] = []
            parsed_data["swn_history"] = []

            # Скорость
            if swv_data and not swv_data.get("error") and "data" in swv_data:
                sw_arr = [x for x in swv_data["data"] if isinstance(x, dict) and self._is_valid_value(x.get("v"))]
                if sw_arr:
                    parsed_data["swv_current"] = sw_arr[0]["v"]
                    parsed_data["swv_history"] = sw_arr[:60]

            # Bt
            if swbt_data and not swbt_data.get("error") and "data" in swbt_data:
                bt_arr = [x for x in swbt_data["data"] if isinstance(x, dict) and self._is_valid_value(x.get("bt"))]
                if bt_arr:
                    parsed_data["sw_bt"] = str(bt_arr[0].get("bt", "0.0"))
                    parsed_data["swbt_history"] = bt_arr[:60]

            # Bz (допускает минусовые значения, но не -9999)
            if swbz_data and not swbz_data.get("error") and "data" in swbz_data:
                bz_arr = [x for x in swbz_data["data"] if isinstance(x, dict) and self._is_valid_bz(x.get("bz"))]
                if bz_arr:
                    parsed_data["sw_bz"] = str(bz_arr[0].get("bz", "0.0"))
                    parsed_data["swbz_history"] = bz_arr[:60]

            # Температура
            if swt_data and not swt_data.get("error") and "data" in swt_data:
                t_arr = [x for x in swt_data["data"] if isinstance(x, dict) and self._is_valid_value(x.get("t"))]
                if t_arr:
                    parsed_data["sw_temp"] = str(t_arr[0].get("t", "0"))
                    parsed_data["swt_history"] = t_arr[:60]

            # Плотность
            if swn_data and not swn_data.get("error") and "data" in swn_data:
                n_arr = [x for x in swn_data["data"] if isinstance(x, dict) and self._is_valid_value(x.get("n"))]
                if n_arr:
                    parsed_data["sw_density"] = str(n_arr[0].get("n", "0.0"))
                    parsed_data["swn_history"] = n_arr[:60]


            # 6. ВЕРОЯТНОСТЬ БУРЬ И ДЕТАЛЬНЫЙ 3-ДНЕВНЫЙ ПРОГНОЗ
            parsed_data["storm_prob_today"] = [15, 30, 55]
            parsed_data["storm_prob_tomorrow"] = [40, 40, 20]
            if noaa_prob_raw and isinstance(noaa_prob_raw, list) and len(noaa_prob_raw) > 0:
                try:
                    p_today = noaa_prob_raw[0]
                    p_tmrw = noaa_prob_raw[1] if len(noaa_prob_raw) > 1 else p_today
                    parsed_data["storm_prob_today"] = [
                        int(p_today.get("no_storm", 15)),
                        int(p_today.get("minor_storm", 35)),
                        int(p_today.get("major_storm", 50))
                    ]
                    parsed_data["storm_prob_tomorrow"] = [
                        int(p_tmrw.get("no_storm", 40)),
                        int(p_tmrw.get("minor_storm", 40)),
                        int(p_tmrw.get("major_storm", 20))
                    ]
                except Exception:
                    pass

            parsed_data["xras_storm_prob_today"] = [100, 0, 0]
            parsed_data["xras_storm_prob_tomorrow"] = [100, 0, 0]
            parsed_data["forecast_3d_array"] = [] 
            
            if kpf_3d_data and not kpf_3d_data.get("error") and "data" in kpf_3d_data:
                parsed_data["forecast_3d_array"] = kpf_3d_data["data"] 
                
                for day in kpf_3d_data["data"]:
                    try:
                        p4 = int(day.get("p4", 0))
                        p5 = int(day.get("p5", 0))
                        p6 = int(day.get("p6", 0))
                        p7 = int(day.get("p7", 0))
                        
                        prob_yellow = p4
                        prob_red = p5 + p6 + p7
                        prob_green = max(0, 100 - prob_yellow - prob_red)
                        calc_prob = [prob_green, prob_yellow, prob_red]
                        
                        if day.get("time") == today_str:
                            parsed_data["xras_storm_prob_today"] = calc_prob
                        elif day.get("time") == tmrw_str:
                            parsed_data["xras_storm_prob_tomorrow"] = calc_prob
                    except Exception:
                        pass

            # 7. СОЛНЕЧНЫЕ ПЯТНА
            parsed_data["sunspots_total_groups"] = "0"
            parsed_data["sunspots_total_area"] = "0"
            parsed_data["sunspots_list"] = []

            if active_areas_html:
                soup_aa = BeautifulSoup(active_areas_html, 'html.parser')
                table = soup_aa.select_one('.table_1')
                if table:
                    tbody = table.select_one('tbody')
                    if tbody:
                        groups = 0
                        total_area = 0
                        spots_list = []
                        for tr in tbody.select('tr'):
                            tds = tr.select('td')
                            if len(tds) >= 6:
                                reg = tds[0].text.replace('№', '').strip()
                                area_str = tds[4].text.strip()
                                m_type = tds[5].text.strip()
                                try:
                                    area = int(area_str)
                                except ValueError:
                                    area = 0
                                groups += 1
                                total_area += area
                                spots_list.append({"reg": reg, "area": area, "type": m_type})
                                
                        spots_list.sort(key=lambda x: x["area"], reverse=True)
                        parsed_data["sunspots_total_groups"] = str(groups)
                        parsed_data["sunspots_total_area"] = str(total_area)
                        parsed_data["sunspots_list"] = spots_list[:3]

            return parsed_data

        except Exception as err:
            _LOGGER.exception("Непредвиденная ошибка в координаторе")
            raise UpdateFailed(f"Ошибка обработки данных: {err}") from err
