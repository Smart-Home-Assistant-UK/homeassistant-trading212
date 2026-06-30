from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CoordinatorData, Trading212Coordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: Trading212Coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data

    config = dict(entry.data)
    config["api_key"] = "**REDACTED**"
    if "api_secret" in config:
        config["api_secret"] = "**REDACTED**"

    coordinator_data: dict[str, Any] = {}
    if data is not None:
        coordinator_data = {
            "total_value": data.total_value,
            "currency": data.currency,
            "cash_available": data.cash_available,
            "invested": data.invested,
            "unrealized_pnl": data.unrealized_pnl,
            "realized_pnl": data.realized_pnl,
            "result_percent": data.result_percent,
            "open_positions_count": data.open_positions_count,
            "active_orders_count": data.active_orders_count,
            "total_dividends": data.total_dividends,
            "daily_gain_loss": data.daily_gain_loss,
            "daily_gain_loss_percent": data.daily_gain_loss_percent,
            "positions": [
                {
                    "ticker": pos.ticker,
                    "ticker_slug": pos.ticker_slug,
                    "instrument_name": pos.instrument_name,
                    "quantity": pos.quantity,
                    "value": pos.value,
                    "pnl": pos.pnl,
                    "pnl_percent": pos.pnl_percent,
                }
                for pos in data.positions.values()
            ],
        }

    return {"config": config, "coordinator_data": coordinator_data}
