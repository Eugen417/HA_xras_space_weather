"""Инициализация интеграции ИКИ РАН: Космическая погода."""
import logging
import os
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.frontend import add_extra_js_url

from .const import DOMAIN
from .coordinator import XrasDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Настройка интеграции."""
    
    integration_dir = os.path.dirname(__file__)
    www_dir = os.path.join(integration_dir, "www")
    
    if os.path.exists(www_dir):
        # ИСПОЛЬЗУЕМ БЕЗОПАСНЫЙ URL ЧЕРЕЗ /api/
        url_base = "/api/xras_sw_static"
        
        # 1. Регистрация статического пути
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path=url_base,
                path=www_dir,
                cache_headers=False,
            )
        ])
        
        # 2. Формируем URL
        cache_buster = str(time.time()).replace(".", "")
        js_url = f"{url_base}/space-weather-card.js?v={cache_buster}"
        
        # 3. Безопасная регистрация в Lovelace
        hass.async_create_task(async_register_resource(hass, js_url))
        _LOGGER.info("Запущена фоновая регистрация карточки (версия: %s)", cache_buster)
    else:
        _LOGGER.error("Критическая ошибка: папка www не найдена по пути %s", www_dir)

    # === НАСТРОЙКА ДАТЧИКОВ ===
    hass.data.setdefault(DOMAIN, {})
    city_alias = entry.data.get("city_id", "moscow") 
    
    coordinator = XrasDataUpdateCoordinator(hass, city_alias)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_register_resource(hass: HomeAssistant, url: str):
    """Безопасное добавление карточки в ресурсы Lovelace."""
    try:
        await hass.async_block_till_done()

        lovelace = hass.data.get("lovelace")
        if not lovelace or not hasattr(lovelace, "resources"):
            _LOGGER.debug("Компонент Lovelace не найден, используем add_extra_js_url")
            add_extra_js_url(hass, url)
            return

        resources = lovelace.resources

        if not resources.loaded:
            await resources.async_load()

        existing_id = None
        for res in resources.async_items():
            if "space-weather-card.js" in res.get("url", ""):
                existing_id = res["id"]
                break

        if existing_id:
            await resources.async_update_item(existing_id, {
                "res_type": "module",
                "url": url
            })
            _LOGGER.info("Ресурс карточки xras успешно обновлен")
        else:
            await resources.async_create_item({
                "res_type": "module",
                "url": url
            })
            _LOGGER.info("Карточка xras успешно добавлена в ресурсы Lovelace")

    except Exception as err:
        _LOGGER.error("Ошибка при регистрации ресурса Lovelace: %s", err)
        add_extra_js_url(hass, url)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Удаление интеграции."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
