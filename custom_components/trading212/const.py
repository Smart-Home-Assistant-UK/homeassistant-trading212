# custom_components/trading212/const.py
DOMAIN = "trading212"

CONF_POSITION_SENSORS = "position_sensors"
CONF_PIE_SENSORS = "pie_sensors"

# All sensors the user can choose from, in display order
OPTIONAL_POSITION_SENSOR_OPTIONS: dict[str, str] = {
    "value": "Value ⭐ required by lovelace card",
    "quantity": "Quantity ⭐ required by lovelace card",
    "pnl": "P&L",
    "pnl_percent": "P&L %",
    "average_price": "Average Price",
    "current_price": "Current Price",
}

OPTIONAL_PIE_SENSOR_OPTIONS: dict[str, str] = {
    "value": "Value ⭐ required by lovelace card",
    "invested": "Invested ⭐ required by lovelace card",
    "pnl_percent": "P&L %",
    "pnl": "P&L",
    "progress": "Progress",
    "cash": "Cash",
    "goal": "Goal",
    "dividends_gained": "Dividends Gained",
    "dividends_in_cash": "Dividends in Cash",
    "dividends_reinvested": "Dividends Reinvested",
}

# Defaults for new installs
DEFAULT_POSITION_SENSORS: list[str] = ["value", "quantity", "pnl", "pnl_percent"]
DEFAULT_PIE_SENSORS: list[str] = ["value", "invested", "pnl_percent"]

# All sensors — used as the fallback for pre-feature installs where
# all sensors were created unconditionally (no key stored in config entry)
ALL_POSITION_SENSORS: list[str] = list(OPTIONAL_POSITION_SENSOR_OPTIONS.keys())
ALL_PIE_SENSORS: list[str] = list(OPTIONAL_PIE_SENSOR_OPTIONS.keys())

LIVE_BASE_URL = "https://live.trading212.com"
DEMO_BASE_URL = "https://demo.trading212.com"

ENVIRONMENT_LIVE = "live"
ENVIRONMENT_DEMO = "demo"

CONF_ENVIRONMENT = "environment"
CONF_POLL_INTERVAL = "poll_interval"
CONF_API_SECRET = "api_secret"
CONF_LABEL = "label"

DEFAULT_POLL_INTERVAL = 60
MIN_POLL_INTERVAL = 30

API_ACCOUNT_SUMMARY = "/api/v0/equity/account/summary"
API_POSITIONS = "/api/v0/equity/positions"
API_ORDERS = "/api/v0/equity/orders"
API_DIVIDENDS = "/api/v0/equity/history/dividends"
API_INSTRUMENTS = "/api/v0/equity/metadata/instruments"
API_PIES = "/api/v0/equity/pies"

EVENT_POSITION_OPENED = "trading212_position_opened"
EVENT_POSITION_CLOSED = "trading212_position_closed"
EVENT_DIVIDEND_RECEIVED = "trading212_dividend_received"
EVENT_PIE_CREATED = "trading212_pie_created"
EVENT_PIE_DELETED = "trading212_pie_deleted"
