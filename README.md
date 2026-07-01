# Trading212 Home Assistant Integration

[![GitHub release](https://img.shields.io/github/v/release/Smart-Home-Assistant-UK/homeassistant-trading212)](https://github.com/Smart-Home-Assistant-UK/homeassistant-trading212/releases)
[![codecov](https://codecov.io/gh/Smart-Home-Assistant-UK/homeassistant-trading212/graph/badge.svg)](https://codecov.io/gh/Smart-Home-Assistant-UK/homeassistant-trading212)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://www.home-assistant.io/)
[![Website](https://img.shields.io/badge/Website-smarthomeassistant.co.uk-informational)](https://smarthomeassistant.co.uk/tools/trading212-home-assistant)

A read-only [Home Assistant](https://www.home-assistant.io/) custom component (HACS integration) for [Trading212](https://www.trading212.com/) that exposes your investment portfolio as sensor entities. Track your stocks, ETFs, and ISA — account summary, individual positions, pies, daily movers, and dividends — directly in Home Assistant dashboards and automations.

> **Full documentation, screenshots, and setup walkthrough:** [smarthomeassistant.co.uk/tools/trading212-home-assistant](https://smarthomeassistant.co.uk/tools/trading212-home-assistant)

> **Don't have a Trading212 account yet?** Sign up with [this referral link](https://www.trading212.com/invite/1BlRG9Ii19) and we both receive a free share worth up to £100.

![Health card](docs/screenshots/default/health-card.png)

---

## Requirements

- Home Assistant 2024.1 or later
- A Trading212 account (Invest, ISA, or Demo)
- A Trading212 API key — generate one at **Settings → API** in the Trading212 app

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations → Explore & Download Repositories**
2. Search for **Trading212** and install
3. Restart Home Assistant

### Manual

Copy the `custom_components/trading212` folder into your HA `config/custom_components/` directory and restart.

---

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for **Trading212**
3. Enter your API key, choose environment (Live or Demo), and set a poll interval
4. Optionally set an **Account Label** if you're adding more than one account (see [Multiple accounts](#multiple-accounts))
5. Optionally open **Configure** on the integration to choose which per-position and per-pie sensors to enable (see [Sensor selection](#sensor-selection))

If you have both Live and Demo accounts, add the integration twice — once per environment.

---

## Sensors

### Account

| Sensor | Description |
|--------|-------------|
| `sensor.trading212_total_value` | Total portfolio value |
| `sensor.trading212_invested` | Total cost basis |
| `sensor.trading212_unrealized_pnl` | Open profit / loss |
| `sensor.trading212_realized_pnl` | All-time realised gains |
| `sensor.trading212_result_percent` | Overall return % |
| `sensor.trading212_cash_available` | Uninvested cash |
| `sensor.trading212_cash_in_pies` | Cash held inside pies |
| `sensor.trading212_total_dividends` | Total dividends received |
| `sensor.trading212_open_positions_count` | Number of open positions |
| `sensor.trading212_active_orders_count` | Pending orders |
| `sensor.trading212_daily_gain_loss` | Today's P&L |
| `sensor.trading212_daily_gain_loss_percent` | Today's return % |
| `sensor.trading212_top_daily_mover` | Best performer today |
| `sensor.trading212_bottom_daily_mover` | Worst performer today |
| `sensor.trading212_biggest_daily_gain` | Largest gain today |
| `sensor.trading212_biggest_daily_loss` | Largest loss today |
| `sensor.trading212_last_updated` | Last successful poll |

### Per position

Up to six sensors per holding — you choose which to enable via **Configure → Sensor selection** (see [Sensor selection](#sensor-selection) below). The slug is the ticker lowercased with non-alphanumeric characters replaced by `_` (e.g. `VWRL_EQ` → `vwrl_eq`):

| Sensor | Default | Description |
|--------|---------|-------------|
| `sensor.trading212_<slug>_value` | ✓ | Current market value |
| `sensor.trading212_<slug>_quantity` | ✓ | Shares held |
| `sensor.trading212_<slug>_pnl` | ✓ | Unrealised P&L |
| `sensor.trading212_<slug>_pnl_percent` | ✓ | Return % |
| `sensor.trading212_<slug>_avg_price` | | Average purchase price |
| `sensor.trading212_<slug>_current_price` | | Current market price |

### Per pie

> **What are Pies?** Pies are Trading212's built-in portfolio buckets that let you group stocks and ETFs with target allocations and auto-invest rules. Each pie appears as its own set of sensors here.

Up to ten sensors per pie — you choose which to enable via **Configure → Sensor selection**. The slug is the pie name lowercased with spaces and symbols replaced by `_` (e.g. `Aggressive but Safe` → `aggressive_but_safe`):

| Sensor | Default | Description |
|--------|---------|-------------|
| `sensor.trading212_<slug>_value` | ✓ | Pie market value |
| `sensor.trading212_<slug>_invested` | ✓ | Amount invested |
| `sensor.trading212_<slug>_pnl_percent` | ✓ | Return % |
| `sensor.trading212_<slug>_pnl` | ✓ | Unrealised P&L |
| `sensor.trading212_<slug>_dividends_gained` | ✓ | Total dividends earned |
| `sensor.trading212_<slug>_cash` | | Uninvested cash in pie |
| `sensor.trading212_<slug>_progress` | | Progress toward goal % |
| `sensor.trading212_<slug>_goal` | | Target goal amount |
| `sensor.trading212_<slug>_dividends_in_cash` | | Dividends held as cash |
| `sensor.trading212_<slug>_dividends_reinvested` | | Dividends reinvested |

The **value** sensor for each pie also exposes a `tickers` state attribute — a list of the instrument tickers held within that pie (e.g. `["VWRL_EQ", "SMGBL_EQ"]`). This is used by the companion lovelace card to filter the asset allocation treemap to a single pie.

### Sensor selection

You can control exactly which per-position and per-pie sensors are created. Go to **Settings → Devices & Services → Trading212 → Configure**, then expand the **Sensor selection** panel.

- **Position sensors**: Value and Quantity are required by the lovelace card (marked ⭐). P&L and P&L % appear in the card's main position view. Average Price and Current Price appear only in the expanded detail panel — enable these if you want to track entry price or build price-alert automations.
- **Pie sensors**: Value and Invested are required by the lovelace card (marked ⭐). The remaining sensors are opt-in.

Sensors you disable are removed as entities; sensors you re-enable are recreated on the next poll. Changing sensor selection reloads the integration, which may briefly show a "Needs attention" banner — this clears automatically once the first poll completes.

### Multiple accounts

You can add the integration more than once — for example, your account and a partner's, or a Live account alongside a Demo one. Set an **Account Label** (e.g. `John`) when adding each entry; it's slugified and inserted into every entity ID for that account:

| Label | Resulting prefix |
|-------|-------------------|
| *(none)* | `sensor.trading212_` |
| `John` | `sensor.trading212_john_` |
| `Jane` | `sensor.trading212_jane_` |

The companion lovelace card's `prefix` option points a card at the right account — see the [card repo's Multiple accounts docs](https://github.com/Smart-Home-Assistant-UK/lovelace-trading212-card#multiple-accounts).

---

## Dashboard Examples

Ready-to-use dashboard configs are in [`docs/dashboards/`](docs/dashboards/).

### Trading212 Card (recommended)

The companion [lovelace-trading212-card](https://github.com/Smart-Home-Assistant-UK/lovelace-trading212-card) gives you purpose-built cards that auto-detect your sensors with zero config.

**Install via HACS (custom repository — category: Plugin):**
1. HACS → Frontend → ⋮ → **Custom repositories**
2. URL: `https://github.com/Smart-Home-Assistant-UK/lovelace-trading212-card` · Category: **Plugin**
3. Add → install → reload browser

```yaml
type: custom:investment-health-card
```

```yaml
type: custom:investment-portfolio-card
```

Full dashboard YAML: [`docs/dashboards/investment-card.yaml`](docs/dashboards/investment-card.yaml)

| Health | Portfolio |
|--------|-----------|
| ![Health card](docs/screenshots/default/health-card.png) | ![Portfolio card](docs/screenshots/default/portfolio-card.png) |

![Overview card](docs/screenshots/default/overview-card.png)

| Positions | Positions expanded |
|-----------|--------------------|
| ![Positions card](docs/screenshots/default/positions-card.png) | ![Positions expanded](docs/screenshots/default/positions-card-expanded.png) |

| Pies | Pies expanded |
|------|---------------|
| ![Pies card](docs/screenshots/default/pies-card.png) | ![Pies expanded](docs/screenshots/default/pies-card-expanded.png) |

#### Asset allocation

A squarified treemap showing portfolio weight and P&L, with three modes via `mode` and `pie`:

```yaml
# All positions (default)
type: custom:investment-allocation-card

# Positions within a specific pie
type: custom:investment-allocation-card
pie: aggressive_but_safe

# Pies overview — each block is one pie
type: custom:investment-allocation-card
mode: pies
```

![Asset allocation card](docs/screenshots/default/allocation-card.png)

### Basic (no dependencies)

Works out of the box with a standard Home Assistant install — no extra card types needed.

Full dashboard YAML: [`docs/dashboards/basic.yaml`](docs/dashboards/basic.yaml)

| Overview | Positions | Pies |
|----------|-----------|------|
| ![basic overview](docs/dashboards/screenshots/basic-overview.png) | ![basic positions](docs/dashboards/screenshots/basic-positions.png) | ![basic pies](docs/dashboards/screenshots/basic-pies.png) |

### Mushroom

Requires [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) (available on HACS).

Full dashboard YAML: [`docs/dashboards/mushroom.yaml`](docs/dashboards/mushroom.yaml)

| Overview | Positions | Pies |
|----------|-----------|------|
| ![mushroom overview](docs/dashboards/screenshots/mushroom-overview.png) | ![mushroom positions](docs/dashboards/screenshots/mushroom-positions.png) | ![mushroom pies](docs/dashboards/screenshots/mushroom-pies.png) |

---

## Notes

- **Read-only** — this integration cannot place or cancel orders
- **Poll interval** — minimum 30 s, default 60 s; **60 s is strongly recommended**. The tightest Trading212 API limit is the pies endpoint at 1 request per 30 s — polling at 30 s will hit that limit on every cycle. Each pie also requires an individual API call on first discovery, so initial startup is slightly slower with larger portfolios. If a rate limit is hit mid-poll, the integration backs off automatically and restores the original interval once the limit clears; sensors remain available showing the last known values during this time. If a poll takes longer than the configured interval, the next poll is skipped rather than running two in parallel
- **Daily P&L** — calculated by comparing current values to a snapshot taken at the start of each calendar day; resets at midnight local time

---

## Troubleshooting

**Sensors show `unavailable`**
Check that your API key is valid and has not been revoked. Go to Trading212 → Settings → API and regenerate if needed, then update the integration via Settings → Devices & Services.

**Rate limit errors in the logs**
Increase the poll interval in the integration options. Trading212 enforces per-minute and per-day limits; 60 s is a safe default.

**Daily P&L resets at the wrong time**
Daily gain/loss is calculated against a midnight snapshot using your Home Assistant server's local time. If your HA instance runs in UTC, the reset will happen at midnight UTC rather than your local midnight.

**Pie sensors are missing**
Pie sensors are created from the pie name at setup time. If you rename a pie in Trading212, remove and re-add the integration to regenerate sensor IDs with the new name.

---

## Contributing

Contributions are welcome. Here's how to get started:

### Dev setup

```bash
pip install -r requirements_test.txt
```

### Running tests

```bash
pytest
```

### Guidelines

- Keep the integration **read-only** — no order placement or account mutations
- New sensors should follow the existing naming convention (`sensor.trading212_<slug>_<metric>`)
- Add or update tests for any changed behaviour; the test suite uses `pytest-homeassistant-custom-component` with async mocks via `aioresponses`
- Open an issue before starting large changes so we can align on approach

### What's in scope

- Additional Trading212 API endpoints (dividends history, orders, etc.)
- Bug fixes and accuracy improvements
- Dashboard examples under `docs/dashboards/`
- HACS compatibility improvements

---

## License

[MIT](LICENSE) © Sepehr Sabbagh-pour
