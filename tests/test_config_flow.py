from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import (
    CONF_ENVIRONMENT,
    CONF_LABEL,
    CONF_PIE_SENSORS,
    CONF_POLL_INTERVAL,
    CONF_POSITION_SENSORS,
    DEFAULT_PIE_SENSORS,
    DEFAULT_POSITION_SENSORS,
    DOMAIN,
    ENVIRONMENT_DEMO,
    ENVIRONMENT_LIVE,
)

VALID_INPUT = {
    "api_key": "test_key",
    "api_secret": "test_secret",
    CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
    CONF_POLL_INTERVAL: 60,
    CONF_LABEL: "",
}


_ACCOUNT_SUMMARY = {
    "id": 12345,
    "currency": "GBP",
    "totalValue": 0.0,
    "cash": {"availableToTrade": 0.0, "inPies": 0.0, "reservedForOrders": 0.0},
    "investments": {
        "totalCost": 0.0,
        "unrealizedProfitLoss": 0.0,
        "realizedProfitLoss": 0.0,
        "currentValue": 0.0,
    },
}


@pytest.fixture(autouse=True)
def mock_api_validation():
    def _make_client():
        client = AsyncMock()
        client.get_account_summary.return_value = _ACCOUNT_SUMMARY
        client.get_instruments.return_value = []
        client.get_positions.return_value = []
        client.get_orders.return_value = []
        client.get_dividends.return_value = {"items": [], "nextPageKey": None}
        client.get_pies.return_value = []
        return client

    with patch(
        "custom_components.trading212.config_flow.Trading212Client",
        return_value=_make_client(),
    ) as mock_cls, patch(
        "custom_components.trading212.Trading212Client",
        side_effect=lambda *a, **kw: _make_client(),
    ):
        yield mock_cls


async def _complete_config_flow(hass, user_input, sensor_input=None):
    """Helper: run both steps of the two-step config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    # Step 1 → sensors step
    assert result["type"] == "form"
    assert result["step_id"] == "sensors"
    # Step 2 → create entry (accept defaults if no sensor_input given)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], sensor_input or {}
    )
    return result


async def test_config_flow_user_step_shows_form(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_config_flow_user_step_advances_to_sensors(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] == "form"
    assert result["step_id"] == "sensors"


async def test_config_flow_creates_entry(hass):
    result = await _complete_config_flow(hass, VALID_INPUT)
    assert result["type"] == "create_entry"


async def test_config_flow_sets_title_with_environment(hass):
    result = await _complete_config_flow(hass, VALID_INPUT)
    assert "Demo" in result["title"] or "demo" in result["title"].lower()


async def test_config_flow_title_without_label(hass):
    result = await _complete_config_flow(hass, {**VALID_INPUT, CONF_LABEL: ""})
    assert result["title"] == "Trading212 (Demo)"


async def test_config_flow_title_with_label(hass):
    result = await _complete_config_flow(hass, {**VALID_INPUT, CONF_LABEL: "John"})
    assert result["title"] == "Trading212 – John (Demo)"


async def test_config_flow_invalid_auth_shows_error(hass):
    from custom_components.trading212.api import InvalidAPIKeyError

    with patch(
        "custom_components.trading212.config_flow.Trading212Client"
    ) as mock_cls:
        mock_client = AsyncMock()
        mock_client.get_account_summary.side_effect = InvalidAPIKeyError("bad key")
        mock_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == "form"
    assert result["errors"]["api_key"] == "invalid_auth"


async def test_config_flow_connection_error_shows_error(hass):
    from custom_components.trading212.api import APIConnectionError

    with patch(
        "custom_components.trading212.config_flow.Trading212Client"
    ) as mock_cls:
        mock_client = AsyncMock()
        mock_client.get_account_summary.side_effect = APIConnectionError("timeout")
        mock_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_INPUT
        )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "cannot_connect"


async def test_config_flow_rejects_poll_interval_below_minimum(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**VALID_INPUT, CONF_POLL_INTERVAL: 10},
    )
    assert result["type"] == "form"
    assert CONF_POLL_INTERVAL in result["errors"] or "base" in result["errors"]


# --- Sensor selection in config flow ---

async def test_config_flow_stores_default_position_sensors(hass):
    result = await _complete_config_flow(hass, VALID_INPUT)
    assert result["data"][CONF_POSITION_SENSORS] == DEFAULT_POSITION_SENSORS


async def test_config_flow_stores_default_pie_sensors(hass):
    result = await _complete_config_flow(hass, VALID_INPUT)
    assert result["data"][CONF_PIE_SENSORS] == DEFAULT_PIE_SENSORS


async def test_config_flow_stores_custom_position_sensors(hass):
    result = await _complete_config_flow(
        hass, VALID_INPUT,
        sensor_input={CONF_POSITION_SENSORS: ["value", "pnl_percent"]},
    )
    assert result["data"][CONF_POSITION_SENSORS] == ["value", "pnl_percent"]


async def test_config_flow_stores_custom_pie_sensors(hass):
    result = await _complete_config_flow(
        hass, VALID_INPUT,
        sensor_input={CONF_PIE_SENSORS: ["value", "invested"]},
    )
    assert result["data"][CONF_PIE_SENSORS] == ["value", "invested"]


async def test_options_flow_updates_poll_interval(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_INPUT, entry_id="test")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_POLL_INTERVAL: 120, CONF_ENVIRONMENT: ENVIRONMENT_DEMO}
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_POLL_INTERVAL] == 120


async def test_options_flow_updates_environment(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_INPUT, entry_id="test_env")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 60, CONF_ENVIRONMENT: ENVIRONMENT_LIVE},
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_ENVIRONMENT] == ENVIRONMENT_LIVE


async def test_config_flow_aborts_if_already_configured(hass, mock_api_validation):
    result = await _complete_config_flow(hass, VALID_INPUT)
    assert result["type"] == "create_entry"

    # Second setup with same account+environment — should abort on user step
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


# --- Sensor selection in options flow ---

async def test_options_flow_stores_sensor_selection(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_INPUT, entry_id="test_sel")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POLL_INTERVAL: 60,
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            "sensor_selection": {
                CONF_POSITION_SENSORS: ["value", "pnl_percent"],
                CONF_PIE_SENSORS: ["value"],
            },
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_POSITION_SENSORS] == ["value", "pnl_percent"]
    assert result["data"][CONF_PIE_SENSORS] == ["value"]


async def test_options_flow_sensor_selection_defaults_when_omitted(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_INPUT, entry_id="test_nosel")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 60, CONF_ENVIRONMENT: ENVIRONMENT_DEMO},
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_POSITION_SENSORS] == DEFAULT_POSITION_SENSORS
    assert result["data"][CONF_PIE_SENSORS] == DEFAULT_PIE_SENSORS


async def test_options_flow_sensor_selection_preserved_when_section_omitted(hass):
    """Submitting options without sensor_selection must preserve the saved selection."""
    custom_data = {
        **VALID_INPUT,
        CONF_POSITION_SENSORS: ["value", "pnl_percent"],
        CONF_PIE_SENSORS: ["value"],
    }
    entry = MockConfigEntry(domain=DOMAIN, data=custom_data, entry_id="test_preserve")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 90, CONF_ENVIRONMENT: ENVIRONMENT_DEMO},
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_POSITION_SENSORS] == ["value", "pnl_percent"]
    assert result["data"][CONF_PIE_SENSORS] == ["value"]


async def test_options_flow_invalid_poll_interval_shows_error(hass):
    """Options flow must re-show the form with an error when poll interval is below minimum."""
    entry = MockConfigEntry(domain=DOMAIN, data=VALID_INPUT, entry_id="test_opts_invalid")
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 5, CONF_ENVIRONMENT: ENVIRONMENT_DEMO},
    )
    assert result["type"] == "form"
    assert CONF_POLL_INTERVAL in result["errors"]
    assert result["errors"][CONF_POLL_INTERVAL] == "invalid_poll_interval"


async def test_options_flow_uses_framework_config_entry(hass):
    """OptionsFlow must read config_entry via self.config_entry (HA 2025+ pattern)."""
    from custom_components.trading212.config_flow import Trading212OptionsFlow

    assert "__init__" not in Trading212OptionsFlow.__dict__, (
        "Trading212OptionsFlow must not override __init__; "
        "use self.config_entry provided by the HA framework instead"
    )
