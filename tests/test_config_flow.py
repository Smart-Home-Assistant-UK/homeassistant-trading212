from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import (
    CONF_ENVIRONMENT,
    CONF_POLL_INTERVAL,
    DOMAIN,
    ENVIRONMENT_DEMO,
    ENVIRONMENT_LIVE,
)

VALID_INPUT = {
    "api_key": "test_key",
    CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
    CONF_POLL_INTERVAL: 60,
}


@pytest.fixture(autouse=True)
def mock_api_validation():
    with patch(
        "custom_components.trading212.config_flow.Trading212Client"
    ) as mock_cls:
        mock_client = AsyncMock()
        mock_client.get_account_summary.return_value = {"id": 12345, "currency": "GBP", "totalValue": 1000.0}
        mock_cls.return_value = mock_client
        yield mock_cls


async def test_config_flow_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert result["type"] == "create_entry"
    assert result["data"] == VALID_INPUT


async def test_config_flow_sets_title_with_environment(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], VALID_INPUT
    )
    assert "Demo" in result["title"] or "demo" in result["title"].lower()


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
    # First setup
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
    assert result["type"] == "create_entry"

    # Second setup with same account+environment — should abort
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], VALID_INPUT)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
