import pytest
import aiohttp
from aioresponses import aioresponses

from custom_components.trading212.api import (
    Trading212Client,
    InvalidAPIKeyError,
    RateLimitExceededError,
    APIConnectionError,
    APIResponseError,
)

BASE_URL = "https://demo.trading212.com"
API_KEY = "test_key_123"

ACCOUNT_SUMMARY_RESPONSE = {
    "cash": {"availableToTrade": 1000.50, "inPies": 200.00, "reservedForOrders": 50.00},
    "investments": {
        "currentValue": 5000.00,
        "realizedProfitLoss": 150.00,
        "totalCost": 4750.00,
        "unrealizedProfitLoss": 250.00,
    },
    "id": 12345,
    "currency": "GBP",
    "totalValue": 6250.50,
}

POSITIONS_RESPONSE = [
    {
        "ticker": "AAPL_US_EQ",
        "quantity": 10.5,
        "averagePrice": 150.00,
        "currentPrice": 175.00,
        "ppl": 262.50,
        "fxPpl": 0.00,
    }
]

ORDERS_RESPONSE = [
    {"id": 1, "ticker": "AAPL_US_EQ", "type": "LIMIT", "quantity": 5.0, "limitPrice": 170.00}
]

DIVIDENDS_RESPONSE = {
    "items": [{"ticker": "AAPL_US_EQ", "amount": 5.25, "paidOn": "2024-01-10T00:00:00Z"}],
    "nextPageKey": None,
}

INSTRUMENTS_RESPONSE = [
    {"ticker": "AAPL_US_EQ", "shortName": "Apple", "isin": "US0378331005", "currencyCode": "USD"}
]

PIES_RESPONSE = [
    {
        "id": 1001,
        "cash": 50.0,
        "dividendDetails": {"gained": 10.0, "inCash": 5.0, "reinvested": 5.0},
        "progress": 0.75,
        "status": "ACTIVE",
        "result": {
            "investedValue": 500.0,
            "result": 25.0,
            "resultCoefficient": 0.05,
            "value": 525.0,
        },
        "settings": {"goal": 1000.0, "id": 1001, "name": "Growth Pie"},
    }
]


@pytest.fixture
async def client():
    # Use ThreadedResolver to avoid pycares spawning a daemon thread on teardown,
    # which would trip pytest-homeassistant-custom-component's verify_cleanup fixture.
    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        yield Trading212Client(session, API_KEY, BASE_URL)


async def test_get_account_summary_returns_data(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", payload=ACCOUNT_SUMMARY_RESPONSE)
        result = await client.get_account_summary()
    assert result["totalValue"] == 6250.50
    assert result["currency"] == "GBP"


async def test_get_account_summary_sends_auth_header(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", payload=ACCOUNT_SUMMARY_RESPONSE)
        await client.get_account_summary()
        request = list(m.requests.values())[0][0]
    assert request.kwargs["headers"]["Authorization"] == API_KEY


async def test_get_positions_returns_list(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/positions", payload=POSITIONS_RESPONSE)
        result = await client.get_positions()
    assert len(result) == 1
    assert result[0]["ticker"] == "AAPL_US_EQ"


async def test_get_orders_returns_list(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/orders", payload=ORDERS_RESPONSE)
        result = await client.get_orders()
    assert len(result) == 1


async def test_get_dividends_returns_dict(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/history/dividends", payload=DIVIDENDS_RESPONSE)
        result = await client.get_dividends()
    assert result["items"][0]["amount"] == 5.25


async def test_get_instruments_returns_list(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/metadata/instruments", payload=INSTRUMENTS_RESPONSE)
        result = await client.get_instruments()
    assert result[0]["ticker"] == "AAPL_US_EQ"
    assert result[0]["shortName"] == "Apple"


async def test_401_raises_auth_error(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", status=401)
        with pytest.raises(InvalidAPIKeyError):
            await client.get_account_summary()


async def test_403_raises_auth_error(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", status=403)
        with pytest.raises(InvalidAPIKeyError):
            await client.get_account_summary()


async def test_429_raises_rate_limit_error(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", status=429)
        with pytest.raises(RateLimitExceededError):
            await client.get_account_summary()


async def test_connection_error_raises_connection_error(client):
    with aioresponses() as m:
        m.get(
            f"{BASE_URL}/api/v0/equity/account/summary",
            exception=aiohttp.ClientConnectionError("connection refused"),
        )
        with pytest.raises(APIConnectionError):
            await client.get_account_summary()


async def test_500_raises_api_error(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", status=500)
        with pytest.raises(APIResponseError):
            await client.get_account_summary()


async def test_get_pies_returns_list(client):
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/pies", payload=PIES_RESPONSE)
        result = await client.get_pies()
    assert len(result) == 1
    assert result[0]["id"] == 1001
    assert result[0]["settings"]["name"] == "Growth Pie"


async def test_get_dividends_passes_cursor_param(client):
    """cursor is forwarded as a query parameter when provided."""
    with aioresponses() as m:
        m.get(
            f"{BASE_URL}/api/v0/equity/history/dividends?cursor=abc123",
            payload={"items": [], "nextPageKey": None},
        )
        result = await client.get_dividends(cursor="abc123")
    assert result == {"items": [], "nextPageKey": None}


async def test_get_dividends_no_cursor_sends_no_params(client):
    """No cursor query param is sent when cursor is omitted."""
    with aioresponses() as m:
        m.get(
            f"{BASE_URL}/api/v0/equity/history/dividends",
            payload={"items": [{"reference": "d1", "amount": 5.0}], "nextPageKey": None},
        )
        result = await client.get_dividends()
    assert result["items"][0]["amount"] == 5.0


async def test_429_with_reset_header_sets_reset_at(client):
    """x-ratelimit-reset header must be captured on 429 responses."""
    with aioresponses() as m:
        m.get(
            f"{BASE_URL}/api/v0/equity/account/summary",
            status=429,
            headers={"x-ratelimit-reset": "1751000000"},
        )
        with pytest.raises(RateLimitExceededError) as exc_info:
            await client.get_account_summary()
    assert exc_info.value.reset_at == pytest.approx(1751000000.0)


async def test_429_without_reset_header_has_none_reset_at(client):
    """reset_at must be None when the header is absent."""
    with aioresponses() as m:
        m.get(f"{BASE_URL}/api/v0/equity/account/summary", status=429)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await client.get_account_summary()
    assert exc_info.value.reset_at is None
