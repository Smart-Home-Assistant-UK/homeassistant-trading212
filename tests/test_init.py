from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trading212.const import (
    CONF_ENVIRONMENT,
    CONF_LABEL,
    CONF_POLL_INTERVAL,
    DOMAIN,
    ENVIRONMENT_DEMO,
)


def _make_entry(entry_id, label=""):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "api_key": "test_key",
            CONF_ENVIRONMENT: ENVIRONMENT_DEMO,
            CONF_POLL_INTERVAL: 60,
            CONF_LABEL: label,
        },
        entry_id=entry_id,
    )


@pytest.fixture
def mock_coordinator_patch(mock_coordinator_data):
    with patch(
        "custom_components.trading212.coordinator.Trading212Coordinator._async_update_data",
        return_value=mock_coordinator_data,
    ), patch("custom_components.trading212.api.Trading212Client"):
        yield


async def test_session_stored_per_entry_id(hass, mock_coordinator_patch):
    entry = _make_entry("entry_abc")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert f"entry_abc_session" in hass.data[DOMAIN]
    assert f"{DOMAIN}_session" not in hass.data[DOMAIN]


async def test_two_entries_have_independent_sessions(hass, mock_coordinator_patch):
    entry_a = _make_entry("entry_aaa", label="John")
    entry_b = _make_entry("entry_bbb", label="Jane")
    # Add both before setup — HA loads all registered entries for the domain together
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    await hass.config_entries.async_setup(entry_a.entry_id)
    await hass.async_block_till_done()

    assert "entry_aaa_session" in hass.data[DOMAIN]
    assert "entry_bbb_session" in hass.data[DOMAIN]
    assert hass.data[DOMAIN]["entry_aaa_session"] is not hass.data[DOMAIN]["entry_bbb_session"]


async def test_session_removed_on_unload(hass, mock_coordinator_patch):
    entry = _make_entry("entry_xyz")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert "entry_xyz_session" in hass.data[DOMAIN]

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert "entry_xyz_session" not in hass.data[DOMAIN]


async def test_unloading_one_entry_does_not_affect_other_session(hass, mock_coordinator_patch):
    entry_a = _make_entry("entry_p", label="John")
    entry_b = _make_entry("entry_q", label="Jane")
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    await hass.config_entries.async_setup(entry_a.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_unload(entry_a.entry_id)
    await hass.async_block_till_done()

    assert "entry_p_session" not in hass.data[DOMAIN]
    assert "entry_q_session" in hass.data[DOMAIN]


async def test_options_update_triggers_reload(hass, mock_coordinator_patch):
    """Changing entry options must trigger async_reload via the update listener."""
    entry = _make_entry("entry_reload")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        hass.config_entries.async_update_entry(entry, options={CONF_POLL_INTERVAL: 120})
        await hass.async_block_till_done()

    mock_reload.assert_called_once_with(entry.entry_id)


async def test_session_closed_when_first_refresh_fails(hass):
    """The aiohttp session must be closed if async_config_entry_first_refresh raises."""
    import aiohttp
    from homeassistant.exceptions import ConfigEntryNotReady

    entry = _make_entry("entry_fail")
    entry.add_to_hass(hass)

    closed_sessions: list = []

    real_client_session_init = aiohttp.ClientSession.__init__

    class _TrackingSession(aiohttp.ClientSession):
        async def close(self):
            closed_sessions.append(self)
            await super().close()

    with patch(
        "custom_components.trading212.Trading212Coordinator.async_config_entry_first_refresh",
        side_effect=ConfigEntryNotReady("API down"),
    ), patch(
        "custom_components.trading212.aiohttp.ClientSession",
        _TrackingSession,
    ), patch("custom_components.trading212.api.Trading212Client"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert len(closed_sessions) == 1, "Session must be closed exactly once on failed first refresh"
