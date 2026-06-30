from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
async def setup_integration(hass, mock_config_entry, mock_coordinator_data):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


async def test_diagnostics_redacts_api_key(hass, setup_integration):
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert result["config"]["api_key"] == "**REDACTED**"


async def test_diagnostics_redacts_api_secret(hass, mock_coordinator_data):
    """api_secret must be scrubbed from diagnostics when present (Basic auth users)."""
    from custom_components.trading212.const import CONF_ENVIRONMENT, CONF_POLL_INTERVAL, DOMAIN, ENVIRONMENT_DEMO
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            "api_secret": "super_secret",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
        },
        entry_id="test_secret_redact",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["config"]["api_secret"] == "**REDACTED**"
    assert "super_secret" not in str(result)


async def test_diagnostics_no_api_secret_key_absent(hass, setup_integration):
    """When api_secret is not stored, diagnostics must not add a REDACTED key."""
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert "api_secret" not in result["config"]


async def test_diagnostics_includes_coordinator_data(hass, setup_integration):
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert "coordinator_data" in result
    assert result["coordinator_data"]["total_value"] == 6100.0


async def test_diagnostics_includes_position_count(hass, setup_integration):
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert result["coordinator_data"]["open_positions_count"] == 2
