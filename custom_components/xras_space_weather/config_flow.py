"""Окно настройки интеграции ИКИ РАН: Космическая погода."""
import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CITIES, USER_AGENT, URL_JSON_BASE

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, str]:
    """Проверяем, отвечает ли сервер ИКИ РАН."""
    city_id = data["city_id"]
    test_url = f"{URL_JSON_BASE}/ai_{city_id}.json"
    
    session = async_get_clientsession(hass)
    headers = {"User-Agent": USER_AGENT}
    
    try:
        async with session.get(test_url, headers=headers, timeout=10) as response:
            if response.status != 200:
                raise ValueError("cannot_connect")
            # Проверяем, что нам отдали именно JSON
            await response.json()
    except Exception as err:
        _LOGGER.error("Ошибка подключения к серверу ИКИ РАН: %s", err)
        raise ValueError("cannot_connect") from err

    # Возвращаем красивое название устройства (например, "Космическая погода: Москва")
    city_name = CITIES[city_id]["name"]
    return {"title": f"Космическая погода: {city_name}"}

class XrasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Класс, отвечающий за интерфейс добавления интеграции."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Первый шаг: Пользователь выбирает город."""
        errors = {}

        if user_input is not None:
            try:
                # Проверяем соединение
                info = await validate_input(self.hass, user_input)
                
                # Проверяем, не добавил ли пользователь этот город раньше
                await self.async_set_unique_id(user_input["city_id"])
                self._abort_if_unique_id_configured()
                
                # Создаем запись в Home Assistant!
                return self.async_create_entry(title=info["title"], data=user_input)
            
            except ValueError as err:
                if str(err) == "cannot_connect":
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Неожиданная ошибка")
                errors["base"] = "unknown"

        # Формируем выпадающий список городов из нашего словаря CITIES
        city_options = {key: val["name"] for key, val in CITIES.items()}
        
        # Рисуем формочку
        data_schema = vol.Schema(
            {
                vol.Required("city_id", default="RAL5"): vol.In(city_options),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )