# custom_components/trading212/const.py
DOMAIN = "trading212"

CONF_POSITION_SENSORS = "position_sensors"
CONF_PIE_SENSORS = "pie_sensors"

# All sensor keys, in display order — labels live in translations/en.json under "selector"
ALL_POSITION_SENSORS: list[str] = [
    "value",
    "quantity",
    "pnl",
    "pnl_percent",
    "average_price",
    "current_price",
]

ALL_PIE_SENSORS: list[str] = [
    "value",
    "invested",
    "pnl_percent",
    "pnl",
    "progress",
    "cash",
    "goal",
    "dividends_gained",
    "dividends_in_cash",
    "dividends_reinvested",
]

# Defaults for new installs
DEFAULT_POSITION_SENSORS: list[str] = ["value", "quantity", "pnl", "pnl_percent"]
DEFAULT_PIE_SENSORS: list[str] = ["value", "invested", "pnl_percent"]

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
