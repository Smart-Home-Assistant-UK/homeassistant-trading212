"""Test configuration for Trading212 integration."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import (
    CONF_ENVIRONMENT,
    CONF_POLL_INTERVAL,
    DOMAIN,
    ENVIRONMENT_DEMO,
)
from custom_components.trading212.coordinator import (
    CoordinatorData,
    DailyMover,
    Pie,
    Position,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    return enable_custom_integrations


@pytest.fixture
def mock_config_entry():
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
