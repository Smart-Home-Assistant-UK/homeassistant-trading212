from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def combined_config(entry: ConfigEntry) -> dict:
    return {**entry.data, **entry.options}


def get_enabled_sensor_list(
    entry: ConfigEntry, conf_key: str, fallback: list[str]
) -> list[str]:
    return combined_config(entry).get(conf_key, fallback)
