"""Сенсоры для интеграции ИКИ РАН: Космическая погода. v3.0.3"""
import logging
import json

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CITIES

_LOGGER = logging.getLogger(__name__)

# Базовый список 9 сенсоров, которые включены по умолчанию
BASE_SENSORS = {
    "aurora_probability_local",
    "solar_flare_current_status",
    "solar_flare_last_info",
    "aurora_index_latest",
    "solar_xray_latest",
    "kp_forecast_today",
    "f10_forecast_today",
    "kp_forecast_tomorrow",
    "kp_current",
}

# Полный словарь всех поддерживаемых сенсоров
SENSOR_TYPES = {
    # --- Базовые сенсоры ---
    "aurora_probability_local": {"unit": "%", "icon": "mdi:aurora"},
    "solar_flare_current_status": {"unit": None, "icon": "mdi:white-balance-sunny"},
    "solar_flare_last_info": {"unit": None, "icon": "mdi:information-outline"},
    "aurora_index_latest": {"unit": "AI", "icon": "mdi:chart-bell-curve-cumulative"},
    "solar_xray_latest": {"unit": "W/m²", "icon": "mdi:white-balance-sunny"},
    "kp_forecast_today": {"unit": "Kp", "icon": "mdi:magnet"},
    "f10_forecast_today": {"unit": "sfu", "icon": "mdi:sun-wireless"},
    "kp_forecast_tomorrow": {"unit": "Kp", "icon": "mdi:magnet-on"},
    "kp_current": {"unit": "Kp", "icon": "mdi:magnet"},
    
    # --- Дополнительные сенсоры (деактивированы по умолчанию) ---
    "swv_current": {"unit": "km/s", "icon": "mdi:weather-windy"},
    "xray_current": {"unit": "W/m²", "icon": "mdi:radioactive"},
    "forecast27_max_kp": {"unit": "Kp", "icon": "mdi:calendar-clock"},
    "xras_storm_probability": {"unit": "%", "icon": "mdi:lightning-bolt-circle"},
}

async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсоров."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    city_alias = entry.data["city_id"] 
    
    sensors = []
    for sensor_type, sensor_info in SENSOR_TYPES.items():
        sensors.append(XrasSensor(coordinator, city_alias, sensor_type, sensor_info))
        
    async_add_entities(sensors)


class XrasSensor(CoordinatorEntity, SensorEntity):
    """Класс сенсора с уникальными ID для каждого города."""

    _attr_has_entity_name = True 

    def __init__(self, coordinator, city_alias, sensor_type, sensor_info):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.city_alias = city_alias
        self.sensor_type = sensor_type
        
        city_info = CITIES[city_alias]
        self.city_name = city_info["name"]
        self.english_city_name = city_alias.replace('_', ' ').title()
        
        is_ru = coordinator.hass.config.language.startswith('ru')
        display_city = self.city_name if is_ru else self.english_city_name
        manufacturer_name = "ИКИ РАН" if is_ru else "IKI RAN"
        
        self.entity_id = f"sensor.{city_alias}_{sensor_type}"
        self._attr_translation_key = sensor_type
        self._attr_unique_id = f"xras_{city_alias}_{sensor_type}"
        self._attr_icon = sensor_info["icon"]
        self._attr_native_unit_of_measurement = sensor_info["unit"]
        
        # Деактивация дополнительных сенсоров по умолчанию
        self._attr_entity_registry_enabled_default = sensor_type in BASE_SENSORS
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, city_alias)},
            name=f"Space Weather ({display_city})", 
            manufacturer=manufacturer_name,
            model=f"Space Weather API ({display_city})", 
            entry_type="service",
        )

    @property
    def native_value(self):
        """Получение значения сенсора из координатора."""
        if not self.coordinator.data:
            return None

        if self.sensor_type == "xras_storm_probability":
            probs = self.coordinator.data.get("xras_storm_prob_today", [100, 0, 0])
            return probs[1] + probs[2]
            
        val = self.coordinator.data.get(self.sensor_type)
        
        if val in ("null", "unknown", "", None):
            return None
            
        if self._attr_native_unit_of_measurement is not None:
            try:
                return float(str(val).replace(',', '.'))
            except ValueError:
                return None
                
        return val

    @property
    def extra_state_attributes(self):
        """Дополнительные атрибуты (локация, время обновления, графики и прогнозы)."""
        attrs = {
            "location_name": self.city_name, 
            "location_name_en": self.english_city_name, 
            "city_alias": self.city_alias
        }
        
        if not self.coordinator.data:
            return attrs

        data = self.coordinator.data

        if self.sensor_type == "aurora_index_latest":
            attrs["time"] = data.get("aurora_time", "")
            attrs["aurora_index"] = self.native_value

        elif self.sensor_type == "swv_current":
            attrs["sw_density"] = data.get("sw_density", "0.0")
            attrs["sw_temp"] = data.get("sw_temp", "0")
            attrs["sw_bt"] = data.get("sw_bt", "0.0")
            attrs["sw_bz"] = data.get("sw_bz", "0.0")
            
            history_v = data.get("swv_history", [])
            attrs["history"] = history_v
            attrs["sw_history_v"] = history_v
            attrs["sw_history_n"] = data.get("swn_history", [])
            attrs["sw_history_t"] = data.get("swt_history", [])
            attrs["sw_history_bt"] = data.get("swbt_history", [])
            attrs["sw_history_bz"] = data.get("swbz_history", [])

        elif self.sensor_type == "xray_current":
            attrs["history"] = data.get("xray_history", [])
            attrs["flares_list"] = json.dumps(data.get("flares_list", []))

        elif self.sensor_type == "forecast27_max_kp":
            attrs["forecast_array"] = data.get("forecast27_array", [])

        elif self.sensor_type == "kp_current":
            attrs["status_text"] = data.get("kp_status_text", "")
            attrs["history_3d"] = data.get("kp_3d_array", [])
            attrs["history_month_current"] = data.get("kp_month_array", [])
            attrs["forecast_month_next"] = data.get("forecast27_array", [])
            attrs["storm_prob_today"] = json.dumps(data.get("storm_prob_today", [15, 35, 50]))
            attrs["storm_prob_tomorrow"] = json.dumps(data.get("storm_prob_tomorrow", [63, 25, 12]))

        elif self.sensor_type == "xras_storm_probability":
            # Родные вероятности ИКИ РАН
            attrs["prob_today"] = json.dumps(data.get("xras_storm_prob_today", [100, 0, 0]))
            attrs["prob_tomorrow"] = json.dumps(data.get("xras_storm_prob_tomorrow", [100, 0, 0]))
            
            # --- ВСЕ НУЖНЫЕ ДАННЫЕ ДЛЯ ВИДЖЕТА INKER В ОДНОМ МЕСТЕ ---
            attrs["storm_prob_today"] = json.dumps(data.get("storm_prob_today", [15, 35, 50]))
            attrs["storm_prob_tomorrow"] = json.dumps(data.get("storm_prob_tomorrow", [63, 25, 12]))
            attrs["kp_today"] = data.get("kp_forecast_today", "0")
            attrs["kp_tomorrow"] = data.get("kp_forecast_tomorrow", "0")
            attrs["kp_max_24h"] = data.get("kp_max_24h", "0") # Тот самый точный 24-часовой максимум!
            attrs["forecast_3d_array"] = data.get("forecast_3d_array", [])

        elif self.sensor_type == "solar_flare_current_status":
            attrs["flare_summary"] = data.get("flare_summary", "")
            attrs["flare_index"] = data.get("flare_index", "—")
            attrs["flares_list"] = json.dumps(data.get("flares_list", []))

        elif self.sensor_type == "f10_forecast_today":
            attrs["sunspots_total_groups"] = data.get("sunspots_total_groups", "0")
            attrs["sunspots_total_area"] = data.get("sunspots_total_area", "0")
            attrs["sunspots_list"] = json.dumps(data.get("sunspots_list", []))

        elif self.sensor_type == "aurora_probability_local":
            attrs["history"] = data.get("aurora_history", [])
            attrs["aurora_prob"] = self.native_value

        return attrs
