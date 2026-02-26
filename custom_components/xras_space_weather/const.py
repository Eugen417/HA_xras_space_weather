"""Константы для интеграции ИКИ РАН: Космическая погода."""

DOMAIN = "xras_space_weather"

# Наш спасительный User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Базовые ссылки
URL_JSON_BASE = "https://xras.ru/txt"
URL_HTML_AURORA = "https://xras.ru/aurora.html"
URL_HTML_FLARES = "https://xras.ru/sun_flares.html"

# Интервал обновления (каждые 30 минут)
UPDATE_INTERVAL_MINUTES = 30

# Список городов для меню настройки (id, alias, Название)
CITIES = {
    "RAL5": {"alias": "moscow", "name": "Москва"},
    "S0KJ": {"alias": "saint_petersburg", "name": "Санкт-Петербург"},
    "R6OX": {"alias": "novosibirsk", "name": "Новосибирск"},
    "RHN2": {"alias": "yekaterinburg", "name": "Екатеринбург"},
    "RBM3": {"alias": "kazan", "name": "Казань"},
    "Q4LP": {"alias": "volgograd", "name": "Волгоград"},
    "P7T0": {"alias": "vladivostok", "name": "Владивосток"},
    # Сюда потом перенесем весь остальной список
}