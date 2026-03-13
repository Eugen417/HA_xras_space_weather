"""Окно настройки интеграции ИКИ РАН: Космическая погода."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CITIES, USER_AGENT, URL_JSON_BASE

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass, data):
    city_alias = data["city_id"]
    city_info = CITIES[city_alias]
    city_internal_id = city_info["id"] 
    
    test_url = f"{URL_JSON_BASE}/ai_{city_internal_id}.json"
    session = async_get_clientsession(hass)
    headers = {"User-Agent": USER_AGENT}
    
    try:
        async with session.get(test_url, headers=headers, timeout=10) as response:
            if response.status != 200:
                raise ValueError("cannot_connect")
            await response.json()
    except Exception as err:
        _LOGGER.error("Ошибка подключения: %s", err)
        raise ValueError("cannot_connect")

    # Умное название интеграции в зависимости от языка
    is_ru = hass.config.language.startswith('ru')
    title_city = city_info['name'] if is_ru else city_alias.replace('_', ' ').title()
    title = f"Космическая погода: {title_city}" if is_ru else f"Space Weather: {title_city}"
    
    return {"title": title}

class XrasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(user_input["city_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)
            except ValueError:
                errors["base"] = "cannot_connect"

        # Определяем язык для списка городов
        is_ru = self.hass.config.language.startswith('ru')
        
        # Формируем список с учетом языка (русский или сгенерированный английский)
        options = {}
        for k, v in CITIES.items():
            options[k] = v["name"] if is_ru else k.replace('_', ' ').title()

        # Сортируем строго по алфавиту для удобства
        sorted_options = dict(sorted(options.items(), key=lambda item: item[1]))
        
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required("city_id", default="moscow"): vol.In(sorted_options)
            }), 
            errors=errors
        )
