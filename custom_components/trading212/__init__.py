from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import Trading212Client
from .const import (
    CONF_API_SECRET,
    CONF_ENVIRONMENT,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEMO_BASE_URL,
    DOMAIN,
    ENVIRONMENT_LIVE,
    LIVE_BASE_URL,
)
from .coordinator import Trading212Coordinator

PLATFORMS = ["sensor"]


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api_key = entry.data["api_key"]
    environment = entry.options.get(CONF_ENVIRONMENT, entry.data[CONF_ENVIRONMENT])
    poll_interval = entry.options.get(
        CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    )

    api_secret = entry.data.get(CONF_API_SECRET)
    base_url = LIVE_BASE_URL if environment == ENVIRONMENT_LIVE else DEMO_BASE_URL

    # Use a dedicated session with ThreadedResolver so OS-level DNS is used.
    # This avoids issues with c-ares (aiodns) in environments where the default
    # async resolver fails to contact the system DNS server (e.g. Docker on macOS).
    connector = aiohttp.TCPConnector(resolver=aiohttp.resolver.ThreadedResolver())
    session = aiohttp.ClientSession(connector=connector)

    client = Trading212Client(session, api_key, base_url, api_secret=api_secret)
    coordinator = Trading212Coordinator(hass, client, poll_interval, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await session.close()
        raise

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    hass.data[DOMAIN][f"{entry.entry_id}_session"] = session

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        session: aiohttp.ClientSession | None = hass.data[DOMAIN].pop(
            f"{entry.entry_id}_session", None
        )
        if session:
            await session.close()
    return unload_ok
