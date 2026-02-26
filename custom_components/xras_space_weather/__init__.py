"""Инициализация интеграции ИКИ РАН: Космическая погода."""
import logging
import os
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN
from .coordinator import XrasDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Оставляем только сенсоры! Сущность weather удалена.
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции после выбора города."""
    
    # === РЕГИСТРАЦИЯ ФРОНТЕНДА (JS-КАРТОЧКИ И КАРТИНОК) С ЗАЩИТОЙ ОТ КЭША ===
    integration_dir = os.path.dirname(__file__)
    www_dir = os.path.join(integration_dir, "www")
    
    if os.path.exists(www_dir):
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path="/xras_sw_static",
                path=www_dir,
                cache_headers=False,
            )
        ])
        
        # Генерируем уникальный хэш на основе текущего времени при каждом старте HA.
        # Это гарантирует, что Safari и iOS Companion App скачают свежую версию скрипта.
        cache_buster = str(time.time()).replace(".", "")
        add_extra_js_url(hass, f"/xras_sw_static/space-weather-card.js?v={cache_buster}")
        
        _LOGGER.info("Фронтенд космической погоды успешно зарегистрирован (v=%s)", cache_buster)
    else:
        _LOGGER.error("Папка www не найдена по пути %s", www_dir)
    # =======================================================

    hass.data.setdefault(DOMAIN, {})
    city_alias = entry.data["city_id"]
    
    coordinator = XrasDataUpdateCoordinator(hass, city_alias)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Удаление интеграции."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
