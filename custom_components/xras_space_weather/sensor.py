"""Сенсоры для интеграции ИКИ РАН: Космическая погода."""
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, CITIES

_LOGGER = logging.getLogger(__name__)

# Используем "длинные" ключи, чтобы старые и новые карточки легко их находили через .includes()
SENSOR_TYPES = {
    "aurora_probability_local": {"name": "Aurora Probability Local", "unit": "%", "icon": "mdi:aurora"},
    "solar_flare_current_status": {"name": "Solar Flare Current Status", "unit": None, "icon": "mdi:white-balance-sunny"},
    "solar_flare_last_info": {"name": "Solar Flare Last Info", "unit": None, "icon": "mdi:information-outline"},
    "aurora_index_latest": {"name": "Aurora Index Latest", "unit": "AI", "icon": "mdi:chart-bell-curve-cumulative"},
    "solar_xray_latest": {"name": "Solar X-Ray Latest", "unit": "W/m²", "icon": "mdi:white-balance-sunny"},
    "kp_forecast_today": {"name": "Kp Forecast Today", "unit": "Kp", "icon": "mdi:magnet"},
    "f10_forecast_today": {"name": "F10 Forecast Today", "unit": "sfu", "icon": "mdi:sun-wireless"},
    "kp_forecast_tomorrow": {"name": "Kp Forecast Tomorrow", "unit": "Kp", "icon": "mdi:magnet-on"},
    "kp_current": {"name": "Kp Current", "unit": "Kp", "icon": "mdi:magnet"},
}

async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсоров."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    city_alias = entry.data["city_id"] # Например, "moscow" или "abakan"
    
    sensors = []
    for sensor_type, sensor_info in SENSOR_TYPES.items():
        sensors.append(XrasSensor(coordinator, city_alias, sensor_type, sensor_info))
        
    async_add_entities(sensors)


class XrasSensor(CoordinatorEntity, SensorEntity):
    """Класс сенсора с уникальными ID для каждого города."""

    def __init__(self, coordinator, city_alias, sensor_type, sensor_info):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.city_alias = city_alias
        self.sensor_type = sensor_type
        
        city_info = CITIES[city_alias]
        self.city_name = city_info["name"]
        
        # Уникальный Entity ID (например: sensor.moscow_kp_current)
        self.entity_id = f"sensor.{city_alias}_{sensor_type}"
        
        # Отображаемое имя в интерфейсе: "Kp Current (Москва)"
        self._attr_name = f"{sensor_info['name']} ({self.city_name})"
        
        # Unique ID для внутренних настроек HA (защита от конфликтов)
        self._attr_unique_id = f"xras_{city_alias}_{sensor_type}"
        self._attr_icon = sensor_info["icon"]
        self._attr_native_unit_of_measurement = sensor_info["unit"]
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, city_alias)},
            name=f"Космическая погода ({self.city_name})",
            manufacturer="ИКИ РАН",
            model="Space Weather API",
            entry_type="service",
        )

    @property
    def native_value(self):
        """Получение значения сенсора из координатора."""
        if not self.coordinator.data:
            return "unknown"
        return self.coordinator.data.get(self.sensor_type, "unknown")

    @property
    def extra_state_attributes(self):
        """Дополнительные атрибуты (локация и время обновления)."""
        attrs = {"location_name": self.city_name, "city_alias": self.city_alias}
        if self.sensor_type == "aurora_index_latest" and self.coordinator.data:
            attrs["time"] = self.coordinator.data.get("aurora_time", "")
        return attrs
