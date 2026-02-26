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
    """Настройка интеграции после добавления города."""
    
    # === РЕГИСТРАЦИЯ ФРОНТЕНДА (Bambu Lab Style) ===
    integration_dir = os.path.dirname(__file__)
    www_dir = os.path.join(integration_dir, "www")
    
    if os.path.exists(www_dir):
        # 1. Регистрация статического пути для доступа к файлам и видео
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path="/xras_sw_static",
                path=www_dir,
                cache_headers=False,
            )
        ])
        
        # 2. Динамический хэш для обхода кэша Safari/Companion App
        cache_buster = str(time.time()).replace(".", "")
        js_url = f"/xras_sw_static/space-weather-card.js?v={cache_buster}"
        
        # 3. Умная регистрация в Lovelace Dashboard
        await async_register_resource(hass, js_url)
        _LOGGER.info("Фронтенд успешно зарегистрирован (версия: %s)", cache_buster)
    else:
        _LOGGER.error("Критическая ошибка: папка www не найдена по пути %s", www_dir)

    # === НАСТРОЙКА ДАТЧИКОВ ===
    hass.data.setdefault(DOMAIN, {})
    city_alias = entry.data["city_id"] # ID города (напр. moscow)
    
    coordinator = XrasDataUpdateCoordinator(hass, city_alias)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_register_resource(hass: HomeAssistant, url: str):
    """Автоматическое добавление карточки в ресурсы Lovelace."""
    try:
        # Пытаемся получить доступ к системным ресурсам Lovelace
        # Это "золотой стандарт" для работы с Companion App
        lovelace = hass.data.get("lovelace")
        if lovelace and hasattr(lovelace, "resources"):
            resources = lovelace.resources
            if resources:
                # Находим и удаляем старые версии этой карточки, чтобы не плодить дубликаты
                existing = [
                    res["id"] for res in resources.async_items() 
                    if res["url"].startswith("/xras_sw_static/space-weather-card.js")
                ]
                for res_id in existing:
                    await resources.async_delete_item(res_id)
                
                # Регистрируем новую версию с актуальным хэшем
                await resources.async_create_item({
                    "res_type": "module",
                    "url": url
                })
        else:
            # Если Lovelace недоступен (например, режим YAML), используем стандартный фолбек
            add_extra_js_url(hass, url)
    except Exception as err:
        # Если что-то пошло не так (реестр заблокирован), используем запасной метод
        _LOGGER.debug("Не удалось обновить реестр ресурсов (используем add_extra_js_url): %s", err)
        add_extra_js_url(hass, url)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Удаление интеграции."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
