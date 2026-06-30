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
        "instrument": {"ticker": "AAPL_US_EQ", "name": "Apple"},
        "quantity": 10.0,
        "averagePricePaid": 150.0,
        "currentPrice": 175.0,
        "walletImpact": {
            "unrealizedProfitLoss": 250.0,
            "currentValue": 1750.0,
            "totalCost": 1500.0,
        },
    },
    {
        "instrument": {"ticker": "MSFT_US_EQ", "name": "Microsoft"},
        "quantity": 5.0,
        "averagePricePaid": 300.0,
        "currentPrice": 280.0,
        "walletImpact": {
            "unrealizedProfitLoss": -100.0,
            "currentValue": 1400.0,
            "totalCost": 1500.0,
        },
    },
]

MOCK_ORDERS = [{"id": 1}, {"id": 2}]
MOCK_DIVIDENDS = {
    "items": [
        {"reference": "div_001", "ticker": "AAPL_US_EQ", "amount": 5.0, "paidOn": "2026-06-20"},
        {"reference": "div_002", "ticker": "MSFT_US_EQ", "amount": 3.0, "paidOn": "2026-06-15"},
    ],
    "nextPageKey": None,
}
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

MOCK_PIE_DETAIL = {
    "settings": {"goal": 1000.0, "id": 1001, "name": "Growth Pie"},
    "instruments": [
        {"ticker": "AAPL_US_EQ", "ownedQuantity": 1.0, "currentShare": 0.6, "expectedShare": 0.6, "issues": []},
        {"ticker": "MSFT_US_EQ", "ownedQuantity": 0.5, "currentShare": 0.4, "expectedShare": 0.4, "issues": []},
    ],
}


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get_account_summary.return_value = MOCK_SUMMARY
    client.get_positions.return_value = MOCK_POSITIONS
    client.get_orders.return_value = MOCK_ORDERS
    client.get_dividends.return_value = MOCK_DIVIDENDS
    client.get_instruments.return_value = MOCK_INSTRUMENTS
    client.get_pies.return_value = MOCK_PIES
    client.get_pie.return_value = MOCK_PIE_DETAIL
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


async def test_coordinator_pie_tickers_populated(coordinator):
    pie = coordinator.data.pies["growth_pie"]
    assert pie.tickers == ["AAPL_US_EQ", "MSFT_US_EQ"]


async def test_coordinator_pie_tickers_empty_when_no_instruments(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    mock_client.get_pie.return_value = {"settings": {"name": "Growth Pie", "goal": 0.0}}
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()
    assert coord.data.pies["growth_pie"].tickers == []


async def test_coordinator_pie_slug_collision(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    # Two pies that produce the same base slug
    mock_client.get_pie.return_value = {"settings": {"name": "My Pie", "goal": 0.0}}
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


# --- Event hook tests ---

async def test_no_events_fired_on_first_fetch(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import (
        EVENT_DIVIDEND_RECEIVED,
        EVENT_PIE_CREATED,
        EVENT_PIE_DELETED,
        EVENT_POSITION_CLOSED,
        EVENT_POSITION_OPENED,
    )

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_no_events_first_fetch"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)

    events = []
    for event_type in [
        EVENT_POSITION_OPENED,
        EVENT_POSITION_CLOSED,
        EVENT_PIE_CREATED,
        EVENT_PIE_DELETED,
        EVENT_DIVIDEND_RECEIVED,
    ]:
        hass.bus.async_listen(event_type, lambda e: events.append(e))

    await coord.async_refresh()

    assert events == [], f"Expected no events on first fetch, got: {[e.event_type for e in events]}"


async def test_previous_state_populated_after_first_fetch(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_prev_state_populated"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    assert "aapl_us_eq" in coord._previous_positions
    assert "msft_us_eq" in coord._previous_positions
    assert "growth_pie" in coord._previous_pies
    assert coord._is_first_fetch is False
    assert "div_001" in coord._seen_dividend_ids
    assert "div_002" in coord._seen_dividend_ids


async def test_position_opened_event_fires_on_new_ticker(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_POSITION_OPENED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pos_opened"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # first fetch — no events

    events = []
    hass.bus.async_listen(EVENT_POSITION_OPENED, lambda e: events.append(e))

    mock_client.get_positions.return_value = MOCK_POSITIONS + [
        {
            "ticker": "TSLA_US_EQ",
            "quantity": 2.0,
            "averagePrice": 200.0,
            "currentPrice": 220.0,
            "ppl": 40.0,
            "fxPpl": 0.0,
        }
    ]
    await coord.async_refresh()

    assert len(events) == 1
    assert events[0].data["ticker"] == "TSLA_US_EQ"
    assert events[0].data["quantity"] == 2.0
    assert events[0].data["value"] == pytest.approx(440.0)


async def test_position_closed_event_fires_on_removed_ticker(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_POSITION_CLOSED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pos_closed"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # first fetch — no events

    events = []
    hass.bus.async_listen(EVENT_POSITION_CLOSED, lambda e: events.append(e))

    # Remove AAPL from positions
    mock_client.get_positions.return_value = [MOCK_POSITIONS[1]]
    await coord.async_refresh()

    assert len(events) == 1
    assert events[0].data["ticker"] == "AAPL_US_EQ"
    assert events[0].data["name"] == "Apple"


async def test_no_position_events_when_positions_unchanged(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_POSITION_OPENED, EVENT_POSITION_CLOSED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pos_unchanged"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    events = []
    for t in [EVENT_POSITION_OPENED, EVENT_POSITION_CLOSED]:
        hass.bus.async_listen(t, lambda e: events.append(e))

    await coord.async_refresh()  # same positions

    assert events == []


MOCK_NEW_PIE = {
    "id": 2002,
    "cash": 0.0,
    "dividendDetails": {"gained": 0.0, "inCash": 0.0, "reinvested": 0.0},
    "progress": 0.0,
    "result": {"investedValue": 100.0, "result": 0.0, "resultCoefficient": 0.0, "value": 100.0},
    "settings": {"goal": 500.0, "id": 2002, "name": "New Pie"},
}


async def test_pie_created_event_fires_on_new_pie(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_PIE_CREATED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pie_created"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    events = []
    hass.bus.async_listen(EVENT_PIE_CREATED, lambda e: events.append(e))

    mock_client.get_pies.return_value = MOCK_PIES + [MOCK_NEW_PIE]
    mock_client.get_pie.return_value = MOCK_NEW_PIE
    await coord.async_refresh()

    assert len(events) == 1
    assert events[0].data["pie_id"] == 2002
    assert events[0].data["name"] == "New Pie"
    assert events[0].data["value"] == pytest.approx(100.0)


async def test_pie_deleted_event_fires_on_removed_pie(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_PIE_DELETED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pie_deleted"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    events = []
    hass.bus.async_listen(EVENT_PIE_DELETED, lambda e: events.append(e))

    mock_client.get_pies.return_value = []
    await coord.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["pie_id"] == 1001
    assert events[0].data["name"] == "Growth Pie"


async def test_no_pie_events_when_pies_unchanged(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_PIE_CREATED, EVENT_PIE_DELETED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_pie_unchanged"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    events = []
    for t in [EVENT_PIE_CREATED, EVENT_PIE_DELETED]:
        hass.bus.async_listen(t, lambda e: events.append(e))

    await coord.async_refresh()

    assert events == []


async def test_dividend_received_event_fires_for_new_dividend(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_DIVIDEND_RECEIVED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_div_received"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # seeds div_001 and div_002 — no events

    events = []
    hass.bus.async_listen(EVENT_DIVIDEND_RECEIVED, lambda e: events.append(e))

    mock_client.get_dividends.return_value = {
        "items": [
            {"reference": "div_001", "ticker": "AAPL_US_EQ", "amount": 5.0, "paidOn": "2026-06-20"},
            {"reference": "div_002", "ticker": "MSFT_US_EQ", "amount": 3.0, "paidOn": "2026-06-15"},
            {"reference": "div_003", "ticker": "AAPL_US_EQ", "amount": 6.5, "paidOn": "2026-06-27"},
        ],
        "nextPageKey": None,
    }
    await coord.async_refresh()

    assert len(events) == 1
    assert events[0].data["ticker"] == "AAPL_US_EQ"
    assert events[0].data["name"] == "Apple"
    assert events[0].data["amount"] == pytest.approx(6.5)
    assert events[0].data["paid_on"] == "2026-06-27"
    assert events[0].data["currency"] == "GBP"


async def test_dividend_event_does_not_fire_twice_for_same_id(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_DIVIDEND_RECEIVED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_div_no_repeat"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # seeds existing dividends

    events = []
    hass.bus.async_listen(EVENT_DIVIDEND_RECEIVED, lambda e: events.append(e))

    # Same dividend list — no new IDs
    await coord.async_refresh()
    await coord.async_refresh()

    assert events == []


async def test_dividend_ids_persisted_after_first_fetch(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_div_persist"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    assert "div_001" in coord._seen_dividend_ids
    assert "div_002" in coord._seen_dividend_ids


async def test_rate_limit_returns_stale_data_and_backs_off(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.api import RateLimitExceededError

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_rate_limit_backoff"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # successful first fetch

    stale_data = coord.data
    normal_interval = coord.update_interval

    # Next poll is rate-limited
    mock_client.get_account_summary.side_effect = RateLimitExceededError("rate limited")
    await coord.async_refresh()

    # Stale data is returned — sensors stay available
    assert coord.data is stale_data
    assert coord.last_update_success is True
    # Interval has been backed off
    assert coord.update_interval > normal_interval


async def test_rate_limit_backoff_respects_maximum(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.api import RateLimitExceededError
    from custom_components.trading212.coordinator import _BACKOFF_MAX
    from datetime import timedelta

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_rate_limit_max"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    # Trigger backoff many times
    mock_client.get_account_summary.side_effect = RateLimitExceededError("rate limited")
    for _ in range(10):
        await coord.async_refresh()

    assert coord.update_interval <= _BACKOFF_MAX


async def test_poll_interval_restored_after_rate_limit_clears(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.api import RateLimitExceededError

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_rate_limit_restore"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()

    # Rate limit
    mock_client.get_account_summary.side_effect = RateLimitExceededError("rate limited")
    await coord.async_refresh()
    assert coord.update_interval.total_seconds() > 60

    # Clears
    mock_client.get_account_summary.side_effect = None
    await coord.async_refresh()
    assert coord.update_interval.total_seconds() == 60


async def test_concurrent_update_skipped(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    import asyncio

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_concurrent_skip"
    coord = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord.async_refresh()  # establishes self.data

    call_count_before = mock_client.get_account_summary.call_count

    # Simulate a second call arriving while the lock is held
    async with coord._update_lock:
        result = await coord._async_update_data()

    # Should have returned stale data without making any API calls
    assert result is coord.data
    assert mock_client.get_account_summary.call_count == call_count_before


async def test_dividend_not_refired_after_restart(hass, mock_client):
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock
    from custom_components.trading212.const import EVENT_DIVIDEND_RECEIVED

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_div_restart"

    coord1 = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)
    await coord1.async_refresh()  # seeds div_001 and div_002 to Store

    # Simulate restart: new coordinator instance, same entry_id, same hass
    coord2 = Trading212Coordinator(hass, mock_client, poll_interval=60, config_entry=entry)

    events = []
    hass.bus.async_listen(EVENT_DIVIDEND_RECEIVED, lambda e: events.append(e))
    await coord2.async_refresh()  # should load from Store, not fire anything

    assert events == [], f"Re-fired after restart: {[e.data for e in events]}"


# ---------------------------------------------------------------------------
# get_enabled_sensor_list
# ---------------------------------------------------------------------------
from custom_components.trading212.coordinator import get_enabled_sensor_list
from custom_components.trading212.const import CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS, ALL_POSITION_SENSORS
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.trading212.const import DOMAIN


def _make_entry(data, options=None):
    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options=options or {},
        entry_id="test_helper",
    )


def test_get_enabled_sensor_list_reads_data():
    entry = _make_entry({CONF_POSITION_SENSORS: ["value", "pnl"]})
    assert get_enabled_sensor_list(entry, CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS) == ["value", "pnl"]


def test_get_enabled_sensor_list_options_override_data():
    entry = _make_entry(
        data={CONF_POSITION_SENSORS: ["value"]},
        options={CONF_POSITION_SENSORS: ["value", "pnl_percent"]},
    )
    assert get_enabled_sensor_list(entry, CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS) == ["value", "pnl_percent"]


def test_get_enabled_sensor_list_falls_back_when_absent():
    entry = _make_entry(data={})
    assert get_enabled_sensor_list(entry, CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS) == DEFAULT_POSITION_SENSORS


def test_get_enabled_sensor_list_falls_back_to_all_for_legacy():
    entry = _make_entry(data={})
    assert get_enabled_sensor_list(entry, CONF_POSITION_SENSORS, ALL_POSITION_SENSORS) == ALL_POSITION_SENSORS
