from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import CONF_ENVIRONMENT, CONF_LABEL, CONF_POLL_INTERVAL, DOMAIN, ENVIRONMENT_DEMO
from custom_components.trading212.sensor import _entity_id, _label_slug


@pytest.fixture
async def setup_integration(hass, mock_config_entry, mock_coordinator_data):
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch(
        "custom_components.trading212.api.Trading212Client"
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry


# --- Account sensors ---

async def test_total_value_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_total_value")
    assert state is not None
    assert float(state.state) == 6100.0


async def test_total_value_sensor_currency(hass, setup_integration):
    state = hass.states.get("sensor.trading212_total_value")
    assert state.attributes["unit_of_measurement"] == "GBP"


async def test_cash_available_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_cash_available")
    assert float(state.state) == 1000.0


async def test_unrealized_pnl_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_unrealized_pnl")
    assert float(state.state) == 250.0


async def test_result_percent_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_result_percent")
    assert float(state.state) == pytest.approx(5.26)


async def test_open_positions_count_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_open_positions_count")
    assert int(state.state) == 2


async def test_active_orders_count_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_active_orders_count")
    assert int(state.state) == 1


async def test_daily_gain_loss_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_daily_gain_loss")
    assert float(state.state) == 50.0


async def test_top_daily_mover_sensor_value(hass, setup_integration):
    state = hass.states.get("sensor.trading212_top_daily_mover")
    assert state.state == "Apple"


async def test_top_daily_mover_has_attributes(hass, setup_integration):
    state = hass.states.get("sensor.trading212_top_daily_mover")
    assert state.attributes["ticker"] == "AAPL_US_EQ"
    assert state.attributes["change_pct"] == 6.0


async def test_bottom_daily_mover_sensor_value(hass, setup_integration):
    state = hass.states.get("sensor.trading212_bottom_daily_mover")
    assert state.state == "Microsoft"


async def test_biggest_daily_gain_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_biggest_daily_gain")
    assert float(state.state) == 100.0
    assert state.attributes["ticker"] == "AAPL_US_EQ"


async def test_biggest_daily_loss_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_biggest_daily_loss")
    assert float(state.state) == -50.0


async def test_total_dividends_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_total_dividends")
    assert float(state.state) == 8.0


# --- Per-position sensors ---

async def test_position_value_sensor_created(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_value")
    assert state is not None
    assert float(state.state) == 1750.0


async def test_position_pnl_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_pnl")
    assert float(state.state) == 250.0


async def test_position_pnl_percent_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_pnl_percent")
    assert float(state.state) == pytest.approx(16.67)


async def test_position_quantity_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_quantity")
    assert float(state.state) == 10.0


async def test_position_avg_price_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_avg_price")
    assert float(state.state) == 150.0


async def test_position_current_price_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_current_price")
    assert float(state.state) == 175.0


async def test_position_sensors_created_for_all_holdings(hass, setup_integration):
    assert hass.states.get("sensor.trading212_msft_us_eq_value") is not None


async def test_position_friendly_name_uses_instrument_name(hass, setup_integration):
    state = hass.states.get("sensor.trading212_aapl_us_eq_value")
    assert "Apple" in state.attributes.get("friendly_name", "")


# --- Per-pie sensors ---

async def test_pie_value_sensor_created(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_value")
    assert state is not None
    assert float(state.state) == 525.0


async def test_pie_invested_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_invested")
    assert float(state.state) == 500.0


async def test_pie_pnl_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_pnl")
    assert float(state.state) == 25.0


async def test_pie_pnl_percent_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_pnl_percent")
    assert float(state.state) == pytest.approx(5.0)


async def test_pie_cash_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_cash")
    assert float(state.state) == 50.0


async def test_pie_progress_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_progress")
    assert float(state.state) == pytest.approx(75.0)


async def test_pie_goal_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_goal")
    assert float(state.state) == 1000.0


async def test_pie_dividends_gained_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_dividends_gained")
    assert float(state.state) == 10.0


async def test_pie_dividends_in_cash_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_dividends_in_cash")
    assert float(state.state) == 5.0


async def test_pie_dividends_reinvested_sensor(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_dividends_reinvested")
    assert float(state.state) == 5.0


async def test_pie_value_sensor_currency(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_value")
    assert state.attributes["unit_of_measurement"] == "GBP"


async def test_pie_friendly_name_uses_pie_name(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_value")
    assert "Growth Pie" in state.attributes.get("friendly_name", "")


async def test_pie_value_sensor_exposes_tickers(hass, setup_integration):
    state = hass.states.get("sensor.trading212_growth_pie_value")
    assert state.attributes.get("tickers") == ["AAPL_US_EQ", "MSFT_US_EQ"]


async def test_pie_non_value_sensor_has_no_tickers(hass, setup_integration):
    # tickers attribute must only appear on the value sensor, not every pie sensor
    for key in ("invested", "pnl", "pnl_percent", "cash", "progress", "goal"):
        state = hass.states.get(f"sensor.trading212_growth_pie_{key}")
        assert "tickers" not in (state.attributes if state else {}), key


# --- Label slug helper ---

def test_label_slug_plain():
    coordinator = MagicMock()
    coordinator.config_entry.data = {CONF_LABEL: "John"}
    assert _label_slug(coordinator) == "john"


def test_label_slug_spaces():
    coordinator = MagicMock()
    coordinator.config_entry.data = {CONF_LABEL: "Aggressive but safe"}
    assert _label_slug(coordinator) == "aggressive_but_safe"


def test_label_slug_special_chars():
    coordinator = MagicMock()
    coordinator.config_entry.data = {CONF_LABEL: "U.S. Tech!"}
    assert _label_slug(coordinator) == "u_s_tech"


def test_label_slug_empty():
    coordinator = MagicMock()
    coordinator.config_entry.data = {CONF_LABEL: ""}
    assert _label_slug(coordinator) == ""


def test_label_slug_missing():
    coordinator = MagicMock()
    coordinator.config_entry.data = {}
    assert _label_slug(coordinator) == ""


def test_entity_id_with_slug():
    assert _entity_id("john", "total_value") == "trading212_john_total_value"


def test_entity_id_without_slug():
    assert _entity_id("", "total_value") == "trading212_total_value"


def test_entity_id_multiple_parts():
    assert _entity_id("jane", "aapl_us_eq", "value") == "trading212_jane_aapl_us_eq_value"


# --- Entity IDs with label ---

@pytest.fixture
async def setup_integration_with_label(hass, mock_coordinator_data):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
            CONF_LABEL: "John",
        },
        entry_id="test_entry_labelled",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


async def test_account_sensor_entity_id_prefixed_with_label(hass, setup_integration_with_label):
    state = hass.states.get("sensor.trading212_john_total_value")
    assert state is not None
    assert float(state.state) == 6100.0


async def test_position_sensor_entity_id_prefixed_with_label(hass, setup_integration_with_label):
    state = hass.states.get("sensor.trading212_john_aapl_us_eq_value")
    assert state is not None


async def test_pie_sensor_entity_id_prefixed_with_label(hass, setup_integration_with_label):
    state = hass.states.get("sensor.trading212_john_growth_pie_value")
    assert state is not None


async def test_unlabelled_entity_ids_unchanged(hass, setup_integration):
    # Existing single-account users must not be affected
    assert hass.states.get("sensor.trading212_total_value") is not None
    assert hass.states.get("sensor.trading212_aapl_us_eq_value") is not None
    assert hass.states.get("sensor.trading212_growth_pie_value") is not None
