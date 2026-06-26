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


async def test_diagnostics_includes_coordinator_data(hass, setup_integration):
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert "coordinator_data" in result
    assert result["coordinator_data"]["total_value"] == 6100.0


async def test_diagnostics_includes_position_count(hass, setup_integration):
    result = await async_get_config_entry_diagnostics(hass, setup_integration)
    assert result["coordinator_data"]["open_positions_count"] == 2
