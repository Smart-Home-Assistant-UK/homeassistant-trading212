"""Test configuration for Trading212 integration."""
import gc
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

# ---------------------------------------------------------------------------
# Backfill homeassistant.data_entry_flow.section for HA < 2024.7
# This must run at module import time, before any integration code is loaded.
# ---------------------------------------------------------------------------
import homeassistant.data_entry_flow as _ha_def

if not hasattr(_ha_def, "section"):

    @dataclass
    class _Section:
        """Minimal Section stand-in: a callable that delegates to its schema."""
        schema: vol.Schema
        options: dict

        def __call__(self, value):
            return self.schema(value)

    def _section(schema, options=None):
        return _Section(schema=schema, options=options or {})

    _ha_def.section = _section


from custom_components.trading212.const import (
    ALL_PIE_SENSORS,
    ALL_POSITION_SENSORS,
    CONF_ENVIRONMENT,
    CONF_PIE_SENSORS,
    CONF_POLL_INTERVAL,
    CONF_POSITION_SENSORS,
    DOMAIN,
    ENVIRONMENT_DEMO,
)
from custom_components.trading212.coordinator import (
    CoordinatorData,
    DailyMover,
    Pie,
    Position,
)


@pytest.fixture(autouse=True, scope="session")
def pre_start_pycares_thread():
    # aiohttp uses pycares for async DNS. When a pycares Channel is destroyed it
    # starts a singleton daemon thread (_run_safe_shutdown_loop). If this thread
    # first appears during a test's teardown, verify_cleanup flags it as a new
    # lingering thread. Pre-start it once before any test captures threads_before.
    try:
        import pycares
        ch = pycares.Channel(sock_state_cb=lambda *a, **kw: None)
        del ch
        gc.collect()
        time.sleep(0.05)
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return enable_custom_integrations


@pytest.fixture(autouse=True)
def no_sleep():
    """Patch asyncio.sleep so pie-detail delays don't slow down the test suite."""
    with patch("custom_components.trading212.coordinator.asyncio.sleep", return_value=None):
        yield


@pytest.fixture
def mock_config_entry():
    """Config entry without CONF_POSITION_SENSORS / CONF_PIE_SENSORS.

    Simulates a legacy install (pre-1.3.0) where sensor keys were absent and the
    integration fell back to ALL_POSITION_SENSORS / ALL_PIE_SENSORS.  Tests using
    this fixture implicitly exercise legacy-install mode, not default-install mode.
    Use mock_config_entry_with_sensors for new-install behaviour.
    """
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
        },
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_config_entry_with_sensors():
    """Config entry that mirrors a fresh install with default sensor selections."""
    from custom_components.trading212.const import DEFAULT_PIE_SENSORS, DEFAULT_POSITION_SENSORS

    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
            CONF_POSITION_SENSORS: DEFAULT_POSITION_SENSORS,
            CONF_PIE_SENSORS: DEFAULT_PIE_SENSORS,
        },
        entry_id="test_entry_default",
    )


@pytest.fixture
def mock_coordinator_data():
    positions = {
        "aapl_us_eq": Position(
            ticker="AAPL_US_EQ",
            ticker_slug="aapl_us_eq",
            instrument_name="Apple",
            quantity=10.0,
            average_price=150.0,
            current_price=175.0,
            value=1750.0,
            pnl=250.0,
            pnl_percent=16.67,
        ),
        "msft_us_eq": Position(
            ticker="MSFT_US_EQ",
            ticker_slug="msft_us_eq",
            instrument_name="Microsoft",
            quantity=5.0,
            average_price=300.0,
            current_price=280.0,
            value=1400.0,
            pnl=-100.0,
            pnl_percent=-6.67,
        ),
    }
    pies = {
        "growth_pie": Pie(
            pie_id=1001,
            name="Growth Pie",
            value=525.0,
            invested=500.0,
            pnl=25.0,
            pnl_percent=5.0,
            cash=50.0,
            progress=75.0,
            goal=1000.0,
            dividends_gained=10.0,
            dividends_in_cash=5.0,
            dividends_reinvested=5.0,
            tickers=["AAPL_US_EQ", "MSFT_US_EQ"],
        )
    }
    return CoordinatorData(
        total_value=6100.0,
        cash_available=1000.0,
        cash_in_pies=100.0,
        invested=4750.0,
        unrealized_pnl=250.0,
        realized_pnl=150.0,
        result_percent=5.26,
        currency="GBP",
        positions=positions,
        pies=pies,
        open_positions_count=2,
        active_orders_count=1,
        total_dividends=8.0,
        daily_gain_loss=50.0,
        daily_gain_loss_percent=1.5,
        top_daily_mover=DailyMover(ticker="AAPL_US_EQ", name="Apple", change_value=100.0, change_pct=6.0),
        bottom_daily_mover=DailyMover(ticker="MSFT_US_EQ", name="Microsoft", change_value=-50.0, change_pct=-3.5),
        biggest_daily_gain=DailyMover(ticker="AAPL_US_EQ", name="Apple", change_value=100.0, change_pct=6.0),
        biggest_daily_loss=DailyMover(ticker="MSFT_US_EQ", name="Microsoft", change_value=-50.0, change_pct=-3.5),
        last_updated=datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc),
    )
