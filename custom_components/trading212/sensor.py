from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

import re

from .const import CONF_LABEL, DOMAIN
from .coordinator import CoordinatorData, Pie, Position, Trading212Coordinator


def _label_slug(coordinator: Trading212Coordinator) -> str:
    label = coordinator.config_entry.data.get(CONF_LABEL, "").strip()
    if not label:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _entity_id(label_slug: str, *parts: str) -> str:
    prefix = f"trading212_{label_slug}" if label_slug else "trading212"
    return "_".join([prefix, *parts])


@dataclass(frozen=True, kw_only=True)
class Trading212SensorDescription(SensorEntityDescription):
    value_fn: Callable[[CoordinatorData], Any] | None = None
    attrs_fn: Callable[[CoordinatorData], dict] | None = None
    unit_fn: Callable[[CoordinatorData], str] | None = None


ACCOUNT_SENSOR_DESCRIPTIONS: tuple[Trading212SensorDescription, ...] = (
    Trading212SensorDescription(
        key="total_value",
        name="Total Value",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.total_value,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="cash_available",
        name="Cash Available",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.cash_available,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="cash_in_pies",
        name="Cash in Pies",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.cash_in_pies,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="invested",
        name="Invested",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.invested,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="unrealized_pnl",
        name="Unrealized P&L",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.unrealized_pnl,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="realized_pnl",
        name="Realized P&L",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.realized_pnl,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="result_percent",
        name="Overall Return",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.result_percent, 2),
    ),
    Trading212SensorDescription(
        key="open_positions_count",
        name="Open Positions",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.open_positions_count,
    ),
    Trading212SensorDescription(
        key="active_orders_count",
        name="Active Orders",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.active_orders_count,
    ),
    Trading212SensorDescription(
        key="total_dividends",
        name="Total Dividends",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.total_dividends,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="daily_gain_loss",
        name="Daily Gain/Loss",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.daily_gain_loss,
        unit_fn=lambda d: d.currency,
    ),
    Trading212SensorDescription(
        key="daily_gain_loss_percent",
        name="Daily Gain/Loss %",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.daily_gain_loss_percent, 2),
    ),
    Trading212SensorDescription(
        key="top_daily_mover",
        name="Top Daily Mover",
        value_fn=lambda d: d.top_daily_mover.name if d.top_daily_mover else None,
        attrs_fn=lambda d: {
            "ticker": d.top_daily_mover.ticker,
            "change_value": d.top_daily_mover.change_value,
            "change_pct": d.top_daily_mover.change_pct,
        } if d.top_daily_mover else {},
    ),
    Trading212SensorDescription(
        key="bottom_daily_mover",
        name="Bottom Daily Mover",
        value_fn=lambda d: d.bottom_daily_mover.name if d.bottom_daily_mover else None,
        attrs_fn=lambda d: {
            "ticker": d.bottom_daily_mover.ticker,
            "change_value": d.bottom_daily_mover.change_value,
            "change_pct": d.bottom_daily_mover.change_pct,
        } if d.bottom_daily_mover else {},
    ),
    Trading212SensorDescription(
        key="biggest_daily_gain",
        name="Biggest Daily Gain",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.biggest_daily_gain.change_value if d.biggest_daily_gain else None,
        unit_fn=lambda d: d.currency,
        attrs_fn=lambda d: {
            "ticker": d.biggest_daily_gain.ticker,
            "name": d.biggest_daily_gain.name,
        } if d.biggest_daily_gain else {},
    ),
    Trading212SensorDescription(
        key="biggest_daily_loss",
        name="Biggest Daily Loss",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.biggest_daily_loss.change_value if d.biggest_daily_loss else None,
        unit_fn=lambda d: d.currency,
        attrs_fn=lambda d: {
            "ticker": d.biggest_daily_loss.ticker,
            "name": d.biggest_daily_loss.name,
        } if d.biggest_daily_loss else {},
    ),
    Trading212SensorDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.last_updated,
    ),
)

# Maps Position attr_key → entity ID slug (only entries that differ from attr_key)
_POSITION_ENTITY_SLUG: dict[str, str] = {
    "average_price": "avg_price",
}

POSITION_ATTRS: tuple[tuple[str, str, SensorDeviceClass | None, str | None], ...] = (
    # (attr_key, friendly_suffix, device_class, unit_override)
    ("value", "Value", SensorDeviceClass.MONETARY, None),
    ("pnl", "P&L", SensorDeviceClass.MONETARY, None),
    ("pnl_percent", "P&L %", None, PERCENTAGE),
    ("quantity", "Quantity", None, None),
    ("average_price", "Avg Price", SensorDeviceClass.MONETARY, None),
    ("current_price", "Current Price", SensorDeviceClass.MONETARY, None),
)

PIE_ATTRS: tuple[tuple[str, str, SensorDeviceClass | None, str | None], ...] = (
    ("value",                "Value",                SensorDeviceClass.MONETARY, None),
    ("invested",             "Invested",             SensorDeviceClass.MONETARY, None),
    ("pnl",                  "P&L",                  SensorDeviceClass.MONETARY, None),
    ("pnl_percent",          "P&L %",                None,                       PERCENTAGE),
    ("cash",                 "Cash",                 SensorDeviceClass.MONETARY, None),
    ("progress",             "Progress",             None,                       PERCENTAGE),
    ("goal",                 "Goal",                 SensorDeviceClass.MONETARY, None),
    ("dividends_gained",     "Dividends Gained",     SensorDeviceClass.MONETARY, None),
    ("dividends_in_cash",    "Dividends Cash",       SensorDeviceClass.MONETARY, None),
    ("dividends_reinvested", "Dividends Reinvested", SensorDeviceClass.MONETARY, None),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Trading212Coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        Trading212AccountSensor(coordinator, description)
        for description in ACCOUNT_SENSOR_DESCRIPTIONS
    )

    known_slugs: set[str] = set()

    @callback
    def _add_new_position_sensors() -> None:
        if coordinator.data is None:
            return
        new_slugs = set(coordinator.data.positions.keys()) - known_slugs
        if not new_slugs:
            return
        known_slugs.update(new_slugs)
        async_add_entities(
            Trading212PositionSensor(coordinator, slug, attr_key, suffix, dc, unit)
            for slug in new_slugs
            for attr_key, suffix, dc, unit in POSITION_ATTRS
        )

    _add_new_position_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_position_sensors))

    known_pie_slugs: set[str] = set()

    @callback
    def _add_new_pie_sensors() -> None:
        if coordinator.data is None:
            return
        new_slugs = set(coordinator.data.pies.keys()) - known_pie_slugs
        if not new_slugs:
            return
        known_pie_slugs.update(new_slugs)
        async_add_entities(
            Trading212PieSensor(coordinator, slug, attr_key, suffix, dc, unit)
            for slug in new_slugs
            for attr_key, suffix, dc, unit in PIE_ATTRS
        )

    _add_new_pie_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_pie_sensors))


class Trading212AccountSensor(CoordinatorEntity[Trading212Coordinator], SensorEntity):
    def __init__(
        self,
        coordinator: Trading212Coordinator,
        description: Trading212SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_suggested_object_id = _entity_id(_label_slug(coordinator), description.key)

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object id used to generate the entity_id."""
        return self._attr_suggested_object_id

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn and self.coordinator.data:
            return self.entity_description.unit_fn(self.coordinator.data)
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attrs_fn and self.coordinator.data:
            return self.entity_description.attrs_fn(self.coordinator.data)
        return None


class Trading212PositionSensor(CoordinatorEntity[Trading212Coordinator], SensorEntity):
    def __init__(
        self,
        coordinator: Trading212Coordinator,
        ticker_slug: str,
        attr_key: str,
        name_suffix: str,
        device_class: SensorDeviceClass | None,
        unit_override: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._ticker_slug = ticker_slug
        self._attr_key = attr_key
        self._unit_override = unit_override
        self._attr_device_class = device_class
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{ticker_slug}_{attr_key}"
        )
        self._attr_state_class = (
            SensorStateClass.TOTAL if device_class == SensorDeviceClass.MONETARY
            else SensorStateClass.MEASUREMENT
        )
        # Use a display slug that may differ from attr_key (e.g. avg_price vs average_price)
        entity_slug = _POSITION_ENTITY_SLUG.get(attr_key, attr_key)
        self._attr_suggested_object_id = _entity_id(_label_slug(coordinator), ticker_slug, entity_slug)

    @property
    def suggested_object_id(self) -> str | None:
        """Return suggested object id used to generate the entity_id."""
        return self._attr_suggested_object_id

    @property
    def _position(self) -> Position | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.positions.get(self._ticker_slug)

    @property
    def name(self) -> str:
        pos = self._position
        base = pos.instrument_name if pos else self._ticker_slug.upper()
        suffix_map = {
            "value": "Value",
            "pnl": "P&L",
            "pnl_percent": "P&L %",
            "quantity": "Quantity",
            "average_price": "Avg Price",
            "current_price": "Current Price",
        }
        return f"{base} {suffix_map.get(self._attr_key, self._attr_key)}"

    @property
    def native_value(self) -> Any:
        pos = self._position
        if pos is None:
            return None
        return getattr(pos, self._attr_key, None)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._unit_override:
            return self._unit_override
        if self._attr_device_class == SensorDeviceClass.MONETARY and self.coordinator.data:
            return self.coordinator.data.currency
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._position is not None


class Trading212PieSensor(CoordinatorEntity[Trading212Coordinator], SensorEntity):
    def __init__(
        self,
        coordinator: Trading212Coordinator,
        pie_slug: str,
        attr_key: str,
        name_suffix: str,
        device_class: SensorDeviceClass | None,
        unit_override: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._pie_slug = pie_slug
        self._attr_key = attr_key
        self._unit_override = unit_override
        self._attr_device_class = device_class
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{pie_slug}_{attr_key}"
        )
        self._attr_state_class = (
            SensorStateClass.TOTAL if device_class == SensorDeviceClass.MONETARY
            else SensorStateClass.MEASUREMENT
        )
        self._attr_suggested_object_id = _entity_id(_label_slug(coordinator), pie_slug, attr_key)

    @property
    def suggested_object_id(self) -> str | None:
        return self._attr_suggested_object_id

    @property
    def _pie(self) -> Pie | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.pies.get(self._pie_slug)

    @property
    def name(self) -> str:
        pie = self._pie
        base = pie.name if pie else self._pie_slug.replace("_", " ").title()
        suffix_map = {
            "value": "Value",
            "invested": "Invested",
            "pnl": "P&L",
            "pnl_percent": "P&L %",
            "cash": "Cash",
            "progress": "Progress",
            "goal": "Goal",
            "dividends_gained": "Dividends Gained",
            "dividends_in_cash": "Dividends Cash",
            "dividends_reinvested": "Dividends Reinvested",
        }
        return f"{base} {suffix_map.get(self._attr_key, self._attr_key)}"

    @property
    def native_value(self) -> Any:
        pie = self._pie
        if pie is None:
            return None
        return getattr(pie, self._attr_key, None)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._unit_override:
            return self._unit_override
        if self._attr_device_class == SensorDeviceClass.MONETARY and self.coordinator.data:
            return self.coordinator.data.currency
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        if self._attr_key == "value" and self._pie is not None:
            return {"tickers": self._pie.tickers}
        return None

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._pie is not None
