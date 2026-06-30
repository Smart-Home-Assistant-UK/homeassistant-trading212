from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    APIResponseError,
    InvalidAPIKeyError,
    APIConnectionError,
    RateLimitExceededError,
)
from .const import (
    DOMAIN,
    EVENT_DIVIDEND_RECEIVED,
    EVENT_PIE_CREATED,
    EVENT_PIE_DELETED,
    EVENT_POSITION_CLOSED,
    EVENT_POSITION_OPENED,
)
from .util import get_enabled_sensor_list

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from .api import Trading212Client

_LOGGER = logging.getLogger(__name__)

_BACKOFF_MIN = timedelta(seconds=30)
_BACKOFF_MAX = timedelta(minutes=5)
_BACKOFF_FACTOR = 2


def ticker_to_slug(ticker: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", ticker.lower())


@dataclass
class Position:
    ticker: str
    ticker_slug: str
    instrument_name: str
    quantity: float
    average_price: float
    current_price: float
    value: float
    pnl: float
    pnl_percent: float
    daily_gain_loss: float = 0.0
    daily_gain_loss_percent: float = 0.0


@dataclass
class DailyMover:
    ticker: str
    name: str
    change_value: float
    change_pct: float


@dataclass
class Pie:
    pie_id: int
    name: str
    value: float
    invested: float
    pnl: float
    pnl_percent: float
    cash: float
    progress: float
    goal: float
    dividends_gained: float
    dividends_in_cash: float
    dividends_reinvested: float
    tickers: list[str] = field(default_factory=list)


@dataclass
class CoordinatorData:
    total_value: float
    cash_available: float
    cash_in_pies: float
    invested: float
    unrealized_pnl: float
    realized_pnl: float
    result_percent: float
    currency: str
    positions: dict[str, Position]
    pies: dict[str, Pie]
    open_positions_count: int
    active_orders_count: int
    total_dividends: float
    daily_gain_loss: float
    daily_gain_loss_percent: float
    top_daily_mover: DailyMover | None
    bottom_daily_mover: DailyMover | None
    biggest_daily_gain: DailyMover | None
    biggest_daily_loss: DailyMover | None
    last_updated: datetime | None


class Trading212Coordinator(DataUpdateCoordinator[CoordinatorData]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: Trading212Client,
        poll_interval: int,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self._client = client
        self.config_entry = config_entry
        self._base_poll_interval = poll_interval
        self._update_lock = asyncio.Lock()
        self._instruments: dict[str, str] = {}
        self._pie_details: dict[int, dict] = {}
        self._daily_baseline: dict[str, float] = {}
        self._baseline_date: date | None = None
        self._baseline_dirty: bool = False
        self._store = Store(hass, 1, f"{DOMAIN}.{config_entry.entry_id}.baseline")
        self._previous_positions: dict[str, Position] = {}
        self._previous_pies: dict[str, Pie] = {}
        self._seen_dividend_ids: set[str] = set()
        self._is_first_fetch: bool = True

    async def _async_update_data(self) -> CoordinatorData:
        if self._update_lock.locked():
            _LOGGER.debug("Previous Trading212 update still running; skipping this cycle")
            if self.data is not None:
                return self.data
            raise UpdateFailed("Update already in progress")

        async with self._update_lock:
            return await self._fetch_data()

    async def _fetch_data(self) -> CoordinatorData:
        if not self._instruments:
            try:
                raw = await self._client.get_instruments()
                self._instruments = {
                    i["ticker"]: i.get("shortName", i["ticker"]) for i in raw
                }
            except InvalidAPIKeyError as err:
                raise UpdateFailed(f"Trading212 authentication failed: {err}") from err
            except (APIConnectionError, APIResponseError, RateLimitExceededError):
                _LOGGER.warning("Failed to fetch instruments metadata; using tickers as names")

        try:
            summary = await self._client.get_account_summary()
            positions_raw = await self._client.get_positions()
            orders_raw = await self._client.get_orders()
            div_items = await self._async_fetch_all_dividends()
            pies_raw = await self._client.get_pies()
        except InvalidAPIKeyError as err:
            raise UpdateFailed(f"Trading212 authentication failed: {err}") from err
        except RateLimitExceededError as err:
            self._apply_rate_limit_backoff(err)
            _LOGGER.warning(
                "Rate limited by Trading212; backing off poll interval to %s",
                self.update_interval,
            )
            if self.data is not None:
                return self.data
            raise UpdateFailed(f"Trading212 rate limit exceeded: {err}") from err
        except APIConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Trading212: {err}") from err
        except APIResponseError as err:
            raise UpdateFailed(f"Trading212 API error: {err}") from err

        # Successful poll — restore normal interval if we were backed off.
        self._restore_poll_interval()

        # Load persisted baseline on first call
        if self._baseline_date is None:
            stored = await self._store.async_load()
            if stored and stored.get("date") == str(dt_util.now().date()):
                self._daily_baseline = stored.get("baseline", {})
                self._baseline_date = dt_util.now().date()

        # Reset baseline on new calendar day
        today = dt_util.now().date()
        if self._baseline_date != today:
            self._daily_baseline = {}
            self._baseline_date = today
            self._baseline_dirty = True

        # Parse positions
        positions: dict[str, Position] = {}
        for raw in positions_raw:
            instrument = raw.get("instrument", {})
            ticker = instrument.get("ticker") or raw.get("ticker", "")
            if not ticker:
                continue
            slug = ticker_to_slug(ticker)
            quantity = float(raw.get("quantity", 0))
            avg_price = float(raw.get("averagePricePaid", 0))
            current_price = float(raw.get("currentPrice", 0))
            wallet = raw.get("walletImpact", {})
            pnl = float(wallet.get("unrealizedProfitLoss", 0))
            value = float(wallet.get("currentValue", 0)) or (quantity * current_price)
            cost = float(wallet.get("totalCost", 0)) or (quantity * avg_price)
            pnl_percent = (pnl / cost * 100) if cost > 0 else 0.0
            instrument_name = instrument.get("name") or self._instruments.get(ticker, ticker)
            positions[slug] = Position(
                ticker=ticker,
                ticker_slug=slug,
                instrument_name=instrument_name,
                quantity=quantity,
                average_price=avg_price,
                current_price=current_price,
                value=value,
                pnl=pnl,
                pnl_percent=pnl_percent,
            )

        # Parse pies — fetch individual details once per pie (name, goal, tickers)
        pies: dict[str, Pie] = {}
        for raw in pies_raw if isinstance(pies_raw, list) else []:
            pie_id = int(raw.get("id", 0))
            if pie_id not in self._pie_details:
                try:
                    detail = await self._client.get_pie(pie_id)
                    settings = detail.get("settings", {})
                    self._pie_details[pie_id] = {
                        "name": settings.get("name") or f"Pie {pie_id}",
                        "goal": float(settings.get("goal") or 0),
                        "tickers": [
                            i["ticker"]
                            for i in detail.get("instruments", [])
                            if i.get("ticker")
                        ],
                    }
                except RateLimitExceededError as err:
                    self._apply_rate_limit_backoff(err)
                    _LOGGER.debug("Rate limited fetching pie %s details; will retry", pie_id)
                except Exception as err:
                    _LOGGER.warning(
                        "Failed to fetch details for pie %s: %s; will retry next poll", pie_id, err
                    )
            pie_info = self._pie_details.get(pie_id, {"name": f"Pie {pie_id}", "goal": 0.0, "tickers": []})
            name = pie_info["name"]
            slug = ticker_to_slug(name)
            if slug in pies:
                slug = f"{slug}_{pie_id}"
            result = raw.get("result", {})
            dividend_details = raw.get("dividendDetails", {})
            pies[slug] = Pie(
                pie_id=pie_id,
                name=name,
                value=float(result.get("priceAvgValue", result.get("value", 0))),
                invested=float(result.get("priceAvgInvestedValue", result.get("investedValue", 0))),
                pnl=float(result.get("priceAvgResult", result.get("result", 0))),
                pnl_percent=float(result.get("priceAvgResultCoef", result.get("resultCoefficient", 0))) * 100,
                cash=float(raw.get("cash", 0)),
                progress=float(raw.get("progress") or 0) * 100,
                goal=pie_info["goal"],
                dividends_gained=float(dividend_details.get("gained", 0)),
                dividends_in_cash=float(dividend_details.get("inCash", 0)),
                dividends_reinvested=float(dividend_details.get("reinvested", 0)),
                tickers=pie_info.get("tickers", []),
            )

        # Seed baseline for new positions
        for slug, pos in positions.items():
            if slug not in self._daily_baseline:
                self._daily_baseline[slug] = pos.value
                self._baseline_dirty = True

        # Persist only when the baseline actually changed
        if self._baseline_dirty:
            await self._store.async_save({"date": str(self._baseline_date), "baseline": self._daily_baseline})
            self._baseline_dirty = False

        # Daily gain/loss vs baseline
        daily_gain_loss = sum(
            pos.value - self._daily_baseline.get(slug, pos.value)
            for slug, pos in positions.items()
        )
        baseline_total = sum(
            self._daily_baseline.get(slug, pos.value) for slug, pos in positions.items()
        )
        daily_pct = (daily_gain_loss / baseline_total * 100) if baseline_total > 0 else 0.0

        # Compute movers
        movers = [
            DailyMover(
                ticker=pos.ticker,
                name=pos.instrument_name,
                change_value=pos.value - self._daily_baseline.get(slug, pos.value),
                change_pct=(
                    (pos.value - self._daily_baseline.get(slug, pos.value))
                    / self._daily_baseline[slug]
                    * 100
                )
                if self._daily_baseline.get(slug, 0) > 0
                else 0.0,
            )
            for slug, pos in positions.items()
        ]

        for slug, pos in positions.items():
            baseline = self._daily_baseline.get(slug, pos.value)
            pos.daily_gain_loss = pos.value - baseline
            pos.daily_gain_loss_percent = (pos.daily_gain_loss / baseline * 100) if baseline > 0 else 0.0

        top_candidate = max(movers, key=lambda m: m.change_pct) if movers else None
        bottom_candidate = min(movers, key=lambda m: m.change_pct) if movers else None
        top = top_candidate if top_candidate and top_candidate.change_pct > 0 else None
        bottom = bottom_candidate if bottom_candidate and bottom_candidate.change_pct < 0 else None
        gain_candidate = max(movers, key=lambda m: m.change_value) if movers else None
        loss_candidate = min(movers, key=lambda m: m.change_value) if movers else None
        biggest_gain = gain_candidate if gain_candidate and gain_candidate.change_value > 0 else None
        biggest_loss = loss_candidate if loss_candidate and loss_candidate.change_value < 0 else None

        # Parse summary
        cash = summary.get("cash", {})
        investments = summary.get("investments", {})
        total_cost = float(investments.get("totalCost", 0))
        unrealized_pnl = float(investments.get("unrealizedProfitLoss", 0))
        result_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

        # Sum dividends
        total_dividends = sum(float(d.get("amount", 0)) for d in div_items)

        # --- Automation event hooks ---
        if self._is_first_fetch:
            # Seed all current IDs so historical dividends don't fire events on startup.
            self._seen_dividend_ids = {
                str(d.get("reference", "")) for d in div_items if d.get("reference")
            }
            self._is_first_fetch = False
        else:
            # Position events
            current_slugs = set(positions.keys())
            prev_slugs = set(self._previous_positions.keys())
            for slug in current_slugs - prev_slugs:
                pos = positions[slug]
                self.hass.bus.async_fire(EVENT_POSITION_OPENED, {
                    "ticker": pos.ticker,
                    "name": pos.instrument_name,
                    "value": pos.value,
                    "quantity": pos.quantity,
                })
            for slug in prev_slugs - current_slugs:
                pos = self._previous_positions[slug]
                self.hass.bus.async_fire(EVENT_POSITION_CLOSED, {
                    "ticker": pos.ticker,
                    "name": pos.instrument_name,
                })

            # Pie events — diff by pie_id to handle slug collisions/renames
            current_pie_ids = {p.pie_id for p in pies.values()}
            prev_pie_ids = {p.pie_id for p in self._previous_pies.values()}
            curr_pies_by_id = {p.pie_id: p for p in pies.values()}
            prev_pies_by_id = {p.pie_id: p for p in self._previous_pies.values()}
            for pie_id in current_pie_ids - prev_pie_ids:
                pie = curr_pies_by_id[pie_id]
                self.hass.bus.async_fire(EVENT_PIE_CREATED, {
                    "pie_id": pie_id,
                    "name": pie.name,
                    "value": pie.value,
                })
            for pie_id in prev_pie_ids - current_pie_ids:
                pie = prev_pies_by_id[pie_id]
                self.hass.bus.async_fire(EVENT_PIE_DELETED, {
                    "pie_id": pie_id,
                    "name": pie.name,
                })

            # Dividend events
            for div in div_items:
                div_id = str(div.get("reference", ""))
                if div_id and div_id not in self._seen_dividend_ids:
                    ticker = div.get("ticker", "")
                    self.hass.bus.async_fire(EVENT_DIVIDEND_RECEIVED, {
                        "ticker": ticker,
                        "name": self._instruments.get(ticker, ticker),
                        "amount": float(div.get("amount", 0)),
                        "currency": summary.get("currency", ""),
                        "paid_on": div.get("paidOn", ""),
                    })
            # Prune to only current response IDs — bounds storage to page window size
            self._seen_dividend_ids = {
                str(d.get("reference", "")) for d in div_items if d.get("reference")
            }

        self._previous_positions = positions
        self._previous_pies = pies
        # --- end automation event hooks ---

        return CoordinatorData(
            total_value=float(summary.get("totalValue", 0)),
            cash_available=float(cash.get("availableToTrade", 0)),
            cash_in_pies=float(cash.get("inPies", 0)),
            invested=total_cost,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=float(investments.get("realizedProfitLoss", 0)),
            result_percent=result_percent,
            currency=summary.get("currency", ""),
            positions=positions,
            pies=pies,
            open_positions_count=len(positions),
            active_orders_count=len(orders_raw) if isinstance(orders_raw, list) else 0,
            total_dividends=total_dividends,
            daily_gain_loss=daily_gain_loss,
            daily_gain_loss_percent=daily_pct,
            top_daily_mover=top,
            bottom_daily_mover=bottom,
            biggest_daily_gain=biggest_gain,
            biggest_daily_loss=biggest_loss,
            last_updated=dt_util.now(),
        )

    async def _async_fetch_all_dividends(self) -> list[dict]:
        items: list[dict] = []
        cursor: str | None = None
        while True:
            page = await self._client.get_dividends(cursor=cursor)
            if not isinstance(page, dict):
                break
            items.extend(page.get("items", []))
            cursor = page.get("nextPageKey") or None
            if not cursor:
                break
        return items

    def _apply_rate_limit_backoff(self, err: RateLimitExceededError | None = None) -> None:
        if err is not None and err.reset_at is not None:
            wait_seconds = max(
                err.reset_at - time.time() + 1.0,
                _BACKOFF_MIN.total_seconds(),
            )
            self.update_interval = timedelta(
                seconds=min(wait_seconds, _BACKOFF_MAX.total_seconds())
            )
        else:
            current = self.update_interval or timedelta(seconds=self._base_poll_interval)
            backed_off = min(current * _BACKOFF_FACTOR, _BACKOFF_MAX)
            backed_off = max(backed_off, _BACKOFF_MIN)
            self.update_interval = backed_off

    def _restore_poll_interval(self) -> None:
        base = timedelta(seconds=self._base_poll_interval)
        if self.update_interval != base:
            self.update_interval = base
            _LOGGER.info(
                "Trading212 rate limit resolved; poll interval restored to %ds",
                self._base_poll_interval,
            )
