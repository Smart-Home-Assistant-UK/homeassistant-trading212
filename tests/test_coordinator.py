from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.trading212.coordinator import (
    CoordinatorData,
    DailyMover,
    Pie,
    Position,
    Trading212Coordinator,
    ticker_to_slug,
)

# --- ticker_to_slug ---

def test_ticker_to_slug_lowercases():
    assert ticker_to_slug("AAPL_US_EQ") == "aapl_us_eq"


def test_ticker_to_slug_replaces_dots():
    assert ticker_to_slug("BRK.B_US_EQ") == "brk_b_us_eq"


def test_ticker_to_slug_replaces_hyphens():
    assert ticker_to_slug("BRK-B") == "brk_b"


# --- Coordinator data parsing ---

MOCK_SUMMARY = {
    "cash": {"availableToTrade": 1000.0, "inPies": 100.0, "reservedForOrders": 50.0},
    "investments": {
        "currentValue": 5000.0,
        "realizedProfitLoss": 150.0,
        "totalCost": 4750.0,
        "unrealizedProfitLoss": 250.0,
    },
    "id": 1,
    "currency": "GBP",
    "totalValue": 6100.0,
}

MOCK_POSITIONS = [
    {
        "ticker": "AAPL_US_EQ",
        "quantity": 10.0,
        "averagePrice": 150.0,
        "currentPrice": 175.0,
        "ppl": 250.0,
        "fxPpl": 0.0,
    },
    {
        "ticker": "MSFT_US_EQ",
        "quantity": 5.0,
        "averagePrice": 300.0,
        "currentPrice": 280.0,
        "ppl": -100.0,
        "fxPpl": 0.0,
    },
]

MOCK_ORDERS = [{"id": 1}, {"id": 2}]
MOCK_DIVIDENDS = {"items": [{"amount": 5.0}, {"amount": 3.0}], "nextPageKey": None}
MOCK_INSTRUMENTS = [
    {"ticker": "AAPL_US_EQ", "shortName": "Apple"},
    {"ticker": "MSFT_US_EQ", "shortName": "Microsoft"},
]

MOCK_PIES = [
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
def mock_client():
    client = AsyncMock()
    client.get_account_summary.return_value = MOCK_SUMMARY
    client.get_positions.return_value = MOCK_POSITIONS
    client.get_orders.return_value = MOCK_ORDERS
    client.get_dividends.return_value = MOCK_DIVIDENDS
    client.get_instruments.return_value = MOCK_INSTRUMENTS
    client.get_pies.return_value = MOCK_PIES
    return client


@pytest.fixture
async def coordinator(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()
    return coord


async def test_coordinator_parses_total_value(coordinator):
    assert coordinator.data.total_value == 6100.0


async def test_coordinator_parses_currency(coordinator):
    assert coordinator.data.currency == "GBP"


async def test_coordinator_parses_cash_available(coordinator):
    assert coordinator.data.cash_available == 1000.0


async def test_coordinator_parses_invested(coordinator):
    assert coordinator.data.invested == 4750.0


async def test_coordinator_parses_unrealized_pnl(coordinator):
    assert coordinator.data.unrealized_pnl == 250.0


async def test_coordinator_parses_realized_pnl(coordinator):
    assert coordinator.data.realized_pnl == 150.0


async def test_coordinator_calculates_result_percent(coordinator):
    # 250.0 / 4750.0 * 100 = 5.263...
    assert abs(coordinator.data.result_percent - 5.263) < 0.01


async def test_coordinator_creates_positions(coordinator):
    assert "aapl_us_eq" in coordinator.data.positions
    assert "msft_us_eq" in coordinator.data.positions


async def test_coordinator_position_value(coordinator):
    pos = coordinator.data.positions["aapl_us_eq"]
    assert pos.value == 10.0 * 175.0  # 1750.0


async def test_coordinator_position_pnl(coordinator):
    pos = coordinator.data.positions["aapl_us_eq"]
    assert pos.pnl == 250.0


async def test_coordinator_position_pnl_percent(coordinator):
    pos = coordinator.data.positions["aapl_us_eq"]
    # 250 / (10 * 150) * 100 = 16.666...
    assert abs(pos.pnl_percent - 16.666) < 0.01


async def test_coordinator_uses_instrument_names(coordinator):
    pos = coordinator.data.positions["aapl_us_eq"]
    assert pos.instrument_name == "Apple"


async def test_coordinator_open_positions_count(coordinator):
    assert coordinator.data.open_positions_count == 2


async def test_coordinator_active_orders_count(coordinator):
    assert coordinator.data.active_orders_count == 2


async def test_coordinator_sums_dividends(coordinator):
    assert coordinator.data.total_dividends == 8.0


async def test_daily_baseline_initialized_on_first_run(coordinator):
    # After first run, baseline should be set for all positions
    assert coordinator.data.daily_gain_loss == 0.0  # equal to baseline on first run


async def test_daily_gain_loss_reflects_change(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_2"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # baseline set: AAPL=1750, MSFT=1400

    # Now AAPL goes up by 100
    mock_client.get_positions.return_value = [
        {
            "ticker": "AAPL_US_EQ",
            "quantity": 10.0,
            "averagePrice": 150.0,
            "currentPrice": 185.0,  # was 175
            "ppl": 350.0,
            "fxPpl": 0.0,
        },
        {
            "ticker": "MSFT_US_EQ",
            "quantity": 5.0,
            "averagePrice": 300.0,
            "currentPrice": 280.0,
            "ppl": -100.0,
            "fxPpl": 0.0,
        },
    ]
    await coord.async_refresh()
    # AAPL: 1850 - 1750 = +100, MSFT: 1400 - 1400 = 0
    assert coord.data.daily_gain_loss == pytest.approx(100.0)


async def test_daily_baseline_resets_on_new_day(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_3"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)

    with patch("custom_components.trading212.coordinator.dt_util") as mock_dt:
        mock_dt.now.return_value.date.return_value = date(2026, 6, 25)
        await coord.async_refresh()

        # Move to next day — baseline should reset
        mock_dt.now.return_value.date.return_value = date(2026, 6, 26)
        await coord.async_refresh()

    assert coord.data.daily_gain_loss == 0.0


async def test_top_daily_mover_identified(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_4"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # baseline established

    mock_client.get_positions.return_value = [
        {"ticker": "AAPL_US_EQ", "quantity": 10.0, "averagePrice": 150.0, "currentPrice": 185.0, "ppl": 350.0, "fxPpl": 0.0},
        {"ticker": "MSFT_US_EQ", "quantity": 5.0, "averagePrice": 300.0, "currentPrice": 270.0, "ppl": -150.0, "fxPpl": 0.0},
    ]
    await coord.async_refresh()

    assert coord.data.top_daily_mover.ticker == "AAPL_US_EQ"
    assert coord.data.bottom_daily_mover.ticker == "MSFT_US_EQ"


async def test_coordinator_creates_pies(coordinator):
    assert "growth_pie" in coordinator.data.pies


async def test_coordinator_pie_value(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.value == 525.0


async def test_coordinator_pie_invested(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.invested == 500.0


async def test_coordinator_pie_pnl(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.pnl == 25.0


async def test_coordinator_pie_pnl_percent(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.pnl_percent == pytest.approx(5.0)


async def test_coordinator_pie_cash(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.cash == 50.0


async def test_coordinator_pie_progress(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.progress == pytest.approx(75.0)


async def test_coordinator_pie_goal(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.goal == 1000.0


async def test_coordinator_pie_dividends_gained(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.dividends_gained == 10.0


async def test_coordinator_pie_dividends_in_cash(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.dividends_in_cash == 5.0


async def test_coordinator_pie_dividends_reinvested(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.dividends_reinvested == 5.0


async def test_coordinator_pie_name(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.name == "Growth Pie"


async def test_coordinator_pie_slug_collision(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    # Two pies that produce the same base slug
    mock_client.get_pies.return_value = [
        {
            "id": 1,
            "cash": 0.0,
            "dividendDetails": {"gained": 0.0, "inCash": 0.0, "reinvested": 0.0},
            "progress": 0.0,
            "result": {"investedValue": 0.0, "result": 0.0, "resultCoefficient": 0.0, "value": 0.0},
            "settings": {"goal": 0.0, "id": 1, "name": "My Pie"},
        },
        {
            "id": 2,
            "cash": 0.0,
            "dividendDetails": {"gained": 0.0, "inCash": 0.0, "reinvested": 0.0},
            "progress": 0.0,
            "result": {"investedValue": 0.0, "result": 0.0, "resultCoefficient": 0.0, "value": 0.0},
            "settings": {"goal": 0.0, "id": 2, "name": "My Pie"},
        },
    ]
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pie_collision"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    assert "my_pie" in coord.data.pies
    assert "my_pie_2" in coord.data.pies
