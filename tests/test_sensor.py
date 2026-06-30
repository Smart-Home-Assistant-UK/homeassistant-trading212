from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import (
    ALL_PIE_SENSORS,
    ALL_POSITION_SENSORS,
    CONF_ENVIRONMENT,
    CONF_LABEL,
    CONF_PIE_SENSORS,
    CONF_POLL_INTERVAL,
    CONF_POSITION_SENSORS,
    DEFAULT_PIE_SENSORS,
    DEFAULT_POSITION_SENSORS,
    DOMAIN,
    ENVIRONMENT_DEMO,
)
from custom_components.trading212.sensor import _entity_id, _label_slug, _remove_disabled_entities


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


async def test_label_slug_reads_from_options(hass, mock_coordinator_data):
    """Label set in options (not data) must be reflected in entity slugs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
            CONF_LABEL: "isa",
            CONF_POSITION_SENSORS: ALL_POSITION_SENSORS,
            CONF_PIE_SENSORS: ALL_PIE_SENSORS,
        },
        options={CONF_LABEL: "sipp"},
        entry_id="test_label_opt",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # entity slug should use the options label "sipp", not the data label "isa"
    assert hass.states.get("sensor.trading212_sipp_total_value") is not None
    assert hass.states.get("sensor.trading212_isa_total_value") is None


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


# ---------------------------------------------------------------------------
# Per-metric sensor selection
# ---------------------------------------------------------------------------

def _make_entry_with_selection(position_sensors, pie_sensors, entry_id="test_sel"):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
            CONF_POSITION_SENSORS: position_sensors,
            CONF_PIE_SENSORS: pie_sensors,
        },
        entry_id=entry_id,
    )


async def _setup_with_selection(hass, mock_coordinator_data, position_sensors, pie_sensors, entry_id="test_sel"):
    entry = _make_entry_with_selection(position_sensors, pie_sensors, entry_id)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


# Legacy: no sensor keys in config → all sensors created

async def test_legacy_install_creates_all_position_sensors(hass, setup_integration):
    """Entry without sensor keys must produce every position sensor (backward compat)."""
    for attr in ALL_POSITION_SENSORS:
        slug = "avg_price" if attr == "average_price" else attr
        assert hass.states.get(f"sensor.trading212_aapl_us_eq_{slug}") is not None, attr


async def test_legacy_install_creates_all_pie_sensors(hass, setup_integration):
    """Entry without sensor keys must produce every pie sensor (backward compat)."""
    for attr in ALL_PIE_SENSORS:
        assert hass.states.get(f"sensor.trading212_growth_pie_{attr}") is not None, attr


# Specific selection: only chosen sensors are created

async def test_position_selection_only_creates_chosen_sensors(hass, mock_coordinator_data):
    await _setup_with_selection(hass, mock_coordinator_data, ["value", "pnl_percent"], DEFAULT_PIE_SENSORS)
    assert hass.states.get("sensor.trading212_aapl_us_eq_value") is not None
    assert hass.states.get("sensor.trading212_aapl_us_eq_pnl_percent") is not None
    assert hass.states.get("sensor.trading212_aapl_us_eq_pnl") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_quantity") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_avg_price") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_current_price") is None


async def test_position_selection_applied_to_every_ticker(hass, mock_coordinator_data):
    await _setup_with_selection(hass, mock_coordinator_data, ["value"], DEFAULT_PIE_SENSORS)
    assert hass.states.get("sensor.trading212_aapl_us_eq_value") is not None
    assert hass.states.get("sensor.trading212_msft_us_eq_value") is not None
    assert hass.states.get("sensor.trading212_aapl_us_eq_pnl") is None
    assert hass.states.get("sensor.trading212_msft_us_eq_pnl") is None


async def test_pie_selection_only_creates_chosen_sensors(hass, mock_coordinator_data):
    await _setup_with_selection(hass, mock_coordinator_data, DEFAULT_POSITION_SENSORS, ["value", "invested"])
    assert hass.states.get("sensor.trading212_growth_pie_value") is not None
    assert hass.states.get("sensor.trading212_growth_pie_invested") is not None
    assert hass.states.get("sensor.trading212_growth_pie_pnl") is None
    assert hass.states.get("sensor.trading212_growth_pie_pnl_percent") is None
    assert hass.states.get("sensor.trading212_growth_pie_cash") is None
    assert hass.states.get("sensor.trading212_growth_pie_progress") is None
    assert hass.states.get("sensor.trading212_growth_pie_dividends_gained") is None


async def test_default_position_sensors_created_for_new_install(hass, mock_coordinator_data):
    await _setup_with_selection(hass, mock_coordinator_data, DEFAULT_POSITION_SENSORS, DEFAULT_PIE_SENSORS)
    for attr in DEFAULT_POSITION_SENSORS:
        assert hass.states.get(f"sensor.trading212_aapl_us_eq_{attr}") is not None, attr
    # Non-default sensors must be absent
    assert hass.states.get("sensor.trading212_aapl_us_eq_avg_price") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_current_price") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_daily_gain_loss") is None
    assert hass.states.get("sensor.trading212_aapl_us_eq_daily_gain_loss_percent") is None


async def test_position_daily_gain_loss_sensors_created_when_enabled(hass, mock_coordinator_data):
    from custom_components.trading212.coordinator import Position
    mock_coordinator_data.positions["aapl_us_eq"] = Position(
        ticker="AAPL_US_EQ",
        ticker_slug="aapl_us_eq",
        instrument_name="Apple",
        quantity=10.0,
        average_price=150.0,
        current_price=175.0,
        value=1750.0,
        pnl=250.0,
        pnl_percent=16.67,
        daily_gain_loss=42.5,
        daily_gain_loss_percent=2.5,
    )
    await _setup_with_selection(
        hass,
        mock_coordinator_data,
        ["value", "daily_gain_loss", "daily_gain_loss_percent"],
        DEFAULT_PIE_SENSORS,
    )
    gain = hass.states.get("sensor.trading212_aapl_us_eq_daily_gain_loss")
    pct = hass.states.get("sensor.trading212_aapl_us_eq_daily_gain_loss_percent")
    assert gain is not None
    assert pct is not None
    assert float(gain.state) == pytest.approx(42.5)
    assert float(pct.state) == pytest.approx(2.5)


async def test_default_pie_sensors_created_for_new_install(hass, mock_coordinator_data):
    await _setup_with_selection(hass, mock_coordinator_data, DEFAULT_POSITION_SENSORS, DEFAULT_PIE_SENSORS)
    for attr in DEFAULT_PIE_SENSORS:
        assert hass.states.get(f"sensor.trading212_growth_pie_{attr}") is not None, attr
    # Non-default sensors must be absent
    assert hass.states.get("sensor.trading212_growth_pie_cash") is None
    assert hass.states.get("sensor.trading212_growth_pie_progress") is None
    assert hass.states.get("sensor.trading212_growth_pie_goal") is None


async def test_account_sensors_always_created_regardless_of_selection(hass, mock_coordinator_data):
    """Account-level sensors are never gated by position/pie sensor selection."""
    await _setup_with_selection(hass, mock_coordinator_data, ["value"], ["value"])
    assert hass.states.get("sensor.trading212_total_value") is not None
    assert hass.states.get("sensor.trading212_unrealized_pnl") is not None
    assert hass.states.get("sensor.trading212_daily_gain_loss") is not None


# _remove_disabled_entities

async def test_remove_disabled_entities_clears_stale_registry_entries(hass, mock_coordinator_data):
    """Stale entities in the registry are removed when their unique_id is not in the enabled set."""
    entry = await _setup_with_selection(
        hass, mock_coordinator_data, ALL_POSITION_SENSORS, ALL_PIE_SENSORS, "test_rem"
    )
    registry = er.async_get(hass)

    # Confirm a full-set sensor exists
    ent = registry.async_get("sensor.trading212_aapl_us_eq_avg_price")
    assert ent is not None

    # Now simulate a narrowed-down set that excludes avg_price
    enabled = {
        f"{entry.entry_id}_total_value",
        f"{entry.entry_id}_aapl_us_eq_value",
        f"{entry.entry_id}_aapl_us_eq_pnl",
        f"{entry.entry_id}_msft_us_eq_value",
        f"{entry.entry_id}_msft_us_eq_pnl",
        f"{entry.entry_id}_growth_pie_value",
        f"{entry.entry_id}_growth_pie_invested",
    }
    _remove_disabled_entities(hass, entry, enabled)

    # avg_price is not in the enabled set → must be gone
    assert registry.async_get("sensor.trading212_aapl_us_eq_avg_price") is None
    # value is in the enabled set → must still be present
    assert registry.async_get("sensor.trading212_aapl_us_eq_value") is not None


async def test_remove_disabled_entities_leaves_other_platforms_untouched(hass, mock_coordinator_data):
    """Only entities with platform == DOMAIN should be removed."""
    entry = await _setup_with_selection(
        hass, mock_coordinator_data, ALL_POSITION_SENSORS, ALL_PIE_SENSORS, "test_plat"
    )
    registry = er.async_get(hass)

    # Inject a fake entity from a different platform sharing the same entry
    registry.async_get_or_create(
        "sensor",
        "other_platform",
        "fake_unique_id",
        config_entry=entry,
    )

    _remove_disabled_entities(hass, entry, set())  # empty set → would remove everything in DOMAIN

    # The other-platform entity must survive
    assert registry.async_get_or_create(
        "sensor", "other_platform", "fake_unique_id", config_entry=entry
    ) is not None


# ---------------------------------------------------------------------------
# SensorStateClass correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sensor_key", [
    "unrealized_pnl",
    "realized_pnl",
    "daily_gain_loss",
    "biggest_daily_gain",
    "biggest_daily_loss",
])
async def test_account_pnl_sensors_have_no_state_class(hass, setup_integration, sensor_key):
    """P&L sensors that can go negative must not use TOTAL (which implies non-decreasing).
    HA forbids MEASUREMENT + MONETARY, so these sensors use state_class=None."""
    state = hass.states.get(f"sensor.trading212_{sensor_key}")
    assert state is not None, f"sensor.trading212_{sensor_key} not found"
    assert state.attributes.get("state_class") is None, (
        f"sensor.trading212_{sensor_key} has state_class={state.attributes.get('state_class')!r}, "
        f"expected None (HA forbids MEASUREMENT+MONETARY; TOTAL is semantically wrong for P&L)"
    )


async def test_position_pnl_sensor_has_no_state_class(hass, setup_integration):
    """Per-position P&L sensor must not use TOTAL (can go negative).
    HA forbids MEASUREMENT + MONETARY, so state_class=None."""
    state = hass.states.get("sensor.trading212_aapl_us_eq_pnl")
    assert state is not None
    assert state.attributes.get("state_class") is None


async def test_position_value_sensor_uses_total_state_class(hass, setup_integration):
    """Per-position value sensor (always positive) keeps TOTAL state class."""
    from homeassistant.components.sensor import SensorStateClass

    state = hass.states.get("sensor.trading212_aapl_us_eq_value")
    assert state is not None
    assert state.attributes.get("state_class") == SensorStateClass.TOTAL


async def test_pie_pnl_sensor_has_no_state_class(hass, setup_integration):
    """Per-pie P&L sensor must not use TOTAL (can go negative).
    HA forbids MEASUREMENT + MONETARY, so state_class=None."""
    state = hass.states.get("sensor.trading212_growth_pie_pnl")
    assert state is not None
    assert state.attributes.get("state_class") is None


async def test_pie_value_sensor_uses_total_state_class(hass, setup_integration):
    """Per-pie value sensor (always positive) keeps TOTAL state class."""
    from homeassistant.components.sensor import SensorStateClass

    state = hass.states.get("sensor.trading212_growth_pie_value")
    assert state is not None
    assert state.attributes.get("state_class") == SensorStateClass.TOTAL


async def test_default_install_position_sensor_count(hass, mock_config_entry_with_sensors, mock_coordinator_data):
    """A new install with default sensor selection creates exactly the default sensors per ticker."""
    from custom_components.trading212.const import DEFAULT_POSITION_SENSORS

    mock_config_entry_with_sensors.add_to_hass(hass)
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(mock_config_entry_with_sensors.entry_id)
        await hass.async_block_till_done()

    states = hass.states.async_all("sensor")
    position_sensor_ids = [
        s.entity_id for s in states
        if any(
            f"_{ticker_slug}_" in s.entity_id
            for ticker_slug in ["aapl_us_eq", "msft_us_eq"]
        )
    ]
    # 2 tickers × len(DEFAULT_POSITION_SENSORS) sensors each
    assert len(position_sensor_ids) == 2 * len(DEFAULT_POSITION_SENSORS)


# ---------------------------------------------------------------------------
# None-guard: sensor properties when coordinator.data is None
# ---------------------------------------------------------------------------

async def test_account_sensor_native_value_is_none_when_no_data(hass, mock_coordinator_data):
    """Trading212AccountSensor.native_value must return None when coordinator.data is None."""
    from unittest.mock import MagicMock
    from custom_components.trading212.sensor import Trading212AccountSensor, ACCOUNT_SENSOR_DESCRIPTIONS

    coordinator = MagicMock()
    coordinator.data = None
    coordinator.config_entry.data = {CONF_ENVIRONMENT: ENVIRONMENT_DEMO, CONF_LABEL: ""}
    coordinator.config_entry.options = {}
    coordinator.config_entry.entry_id = "test_none_guard"

    sensor = Trading212AccountSensor(coordinator, ACCOUNT_SENSOR_DESCRIPTIONS[0])
    assert sensor.native_value is None


async def test_position_sensor_returns_none_when_coordinator_data_is_none(hass, mock_coordinator_data):
    """Trading212PositionSensor._position and native_value must return None when data is None."""
    from unittest.mock import MagicMock
    from custom_components.trading212.sensor import Trading212PositionSensor
    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

    coordinator = MagicMock()
    coordinator.data = None
    coordinator.config_entry.data = {CONF_ENVIRONMENT: ENVIRONMENT_DEMO, CONF_LABEL: ""}
    coordinator.config_entry.options = {}
    coordinator.config_entry.entry_id = "test_pos_none"

    sensor = Trading212PositionSensor(
        coordinator, "aapl_us_eq", "value", "Value",
        SensorDeviceClass.MONETARY, None, SensorStateClass.TOTAL
    )
    assert sensor._position is None
    assert sensor.native_value is None


async def test_position_sensor_returns_none_when_ticker_not_in_data(hass, mock_coordinator_data):
    """Trading212PositionSensor.native_value must return None when the ticker is absent from data."""
    from unittest.mock import MagicMock
    from custom_components.trading212.sensor import Trading212PositionSensor
    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

    coordinator = MagicMock()
    coordinator.data.positions = {}  # ticker not present
    coordinator.config_entry.data = {CONF_ENVIRONMENT: ENVIRONMENT_DEMO, CONF_LABEL: ""}
    coordinator.config_entry.options = {}
    coordinator.config_entry.entry_id = "test_pos_missing"

    sensor = Trading212PositionSensor(
        coordinator, "unknown_ticker", "value", "Value",
        SensorDeviceClass.MONETARY, None, SensorStateClass.TOTAL
    )
    assert sensor.native_value is None


async def test_pie_sensor_returns_none_when_coordinator_data_is_none(hass, mock_coordinator_data):
    """Trading212PieSensor._pie and native_value must return None when data is None."""
    from unittest.mock import MagicMock
    from custom_components.trading212.sensor import Trading212PieSensor
    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

    coordinator = MagicMock()
    coordinator.data = None
    coordinator.config_entry.data = {CONF_ENVIRONMENT: ENVIRONMENT_DEMO, CONF_LABEL: ""}
    coordinator.config_entry.options = {}
    coordinator.config_entry.entry_id = "test_pie_none"

    sensor = Trading212PieSensor(
        coordinator, "growth_pie", "value", "Value",
        SensorDeviceClass.MONETARY, None, SensorStateClass.TOTAL
    )
    assert sensor._pie is None
    assert sensor.native_value is None
    assert sensor.native_unit_of_measurement is None
