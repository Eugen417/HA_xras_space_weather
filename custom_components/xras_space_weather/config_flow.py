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
    city_internal_id = city_info["id"] # Получаем QYPM и т.д. для запроса
    
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

    return {"title": f"Космическая погода: {city_info['name']}"}

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

        # Сортируем все 104 города по названию для удобства выбора
        sorted_options = {
            k: v["name"] 
            for k, v in sorted(CITIES.items(), key=lambda item: item[1]["name"])
        }
        
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required("city_id", default="moscow"): vol.In(sorted_options)
            }), 
            errors=errors
        )
