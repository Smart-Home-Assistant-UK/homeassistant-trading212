# Automations with the Trading212 Integration

The Trading212 integration exposes two types of automation hooks:

1. **Custom events** — one-shot HA bus events for transactional occurrences that have no
   persistent sensor state (a dividend landing, a new position opening, etc.)
2. **Sensor-based triggers** — standard HA numeric/state triggers on existing sensors
   (no extra setup needed)

---

## Custom Events

Use an `event` trigger in your automation to listen for these. All events are fired after
the coordinator's sensor data has updated, so sensor state is already current when your
automation runs.

### `trading212_position_opened`

Fires when a new ticker appears in your portfolio.

**Event data:**

| Key | Type | Example |
|---|---|---|
| `ticker` | string | `"AAPL_US_EQ"` |
| `name` | string | `"Apple Inc."` |
| `value` | float | `1500.00` |
| `quantity` | float | `10.0` |

**Example automation:**

```yaml
automation:
  alias: "Trading212 - New Position Alert"
  trigger:
    platform: event
    event_type: trading212_position_opened
  action:
    service: notify.notify
    data:
      message: >
        Opened: {{ trigger.event.data.name }} ({{ trigger.event.data.ticker }})
        — {{ trigger.event.data.quantity }} shares
        worth {{ trigger.event.data.value | round(2) }}
```

---

### `trading212_position_closed`

Fires when a ticker disappears from your portfolio.

**Event data:**

| Key | Type | Example |
|---|---|---|
| `ticker` | string | `"AAPL_US_EQ"` |
| `name` | string | `"Apple Inc."` |

**Example automation:**

```yaml
automation:
  alias: "Trading212 - Position Closed Alert"
  trigger:
    platform: event
    event_type: trading212_position_closed
  action:
    service: notify.notify
    data:
      message: "Closed position: {{ trigger.event.data.name }} ({{ trigger.event.data.ticker }})"
```

---

### `trading212_dividend_received`

Fires when a new dividend payment appears in your history. Each payment fires exactly once —
the event will not re-fire after a Home Assistant restart.

**Event data:**

| Key | Type | Example |
|---|---|---|
| `ticker` | string | `"AAPL_US_EQ"` |
| `name` | string | `"Apple Inc."` |
| `amount` | float | `12.50` |
| `currency` | string | `"GBP"` |
| `paid_on` | string | `"2026-06-25"` |

**Example automation:**

```yaml
automation:
  alias: "Trading212 - Dividend Received"
  trigger:
    platform: event
    event_type: trading212_dividend_received
  action:
    service: notify.notify
    data:
      message: >
        Dividend received: {{ trigger.event.data.amount }} {{ trigger.event.data.currency }}
        from {{ trigger.event.data.name }}
```

---

### `trading212_pie_created`

Fires when a new pie appears in your account.

**Event data:**

| Key | Type | Example |
|---|---|---|
| `pie_id` | int | `42` |
| `name` | string | `"Tech Growth"` |
| `value` | float | `500.00` |

**Example automation:**

```yaml
automation:
  alias: "Trading212 - New Pie Created"
  trigger:
    platform: event
    event_type: trading212_pie_created
  action:
    service: notify.notify
    data:
      message: "New pie created: {{ trigger.event.data.name }}"
```

---

### `trading212_pie_deleted`

Fires when a pie disappears from your account.

**Event data:**

| Key | Type | Example |
|---|---|---|
| `pie_id` | int | `42` |
| `name` | string | `"Tech Growth"` |

**Example automation:**

```yaml
automation:
  alias: "Trading212 - Pie Deleted"
  trigger:
    platform: event
    event_type: trading212_pie_deleted
  action:
    service: notify.notify
    data:
      message: "Pie deleted: {{ trigger.event.data.name }}"
```

---

## Sensor-Based Automations

These patterns use Home Assistant's built-in trigger types against the existing sensors.
No integration changes are needed — set them up directly in the HA automation editor.

### Daily P&L alert

Trigger when your portfolio drops more than a set percentage in a day.

```yaml
automation:
  alias: "Trading212 - Daily Loss Alert"
  trigger:
    platform: numeric_state
    entity_id: sensor.trading212_daily_gain_loss_percent
    below: -3
  action:
    service: notify.notify
    data:
      message: >
        Portfolio is down {{ states('sensor.trading212_daily_gain_loss_percent') }}% today
        ({{ states('sensor.trading212_daily_gain_loss') }} {{ state_attr('sensor.trading212_daily_gain_loss', 'unit_of_measurement') }})
```

---

### Position P&L alert

Trigger when a specific holding drops or gains beyond a threshold.
Replace `aapl_us_eq` with the ticker slug of your position (lowercase, non-alphanumeric replaced by `_`).

```yaml
automation:
  alias: "Trading212 - AAPL Down 5%"
  trigger:
    platform: numeric_state
    entity_id: sensor.trading212_aapl_us_eq_pnl_percent
    below: -5
  action:
    service: notify.notify
    data:
      message: "AAPL is down {{ states('sensor.trading212_aapl_us_eq_pnl_percent') }}%"
```

---

### Low cash warning

Trigger when available cash drops below a threshold.

```yaml
automation:
  alias: "Trading212 - Low Cash Warning"
  trigger:
    platform: numeric_state
    entity_id: sensor.trading212_cash_available
    below: 100
  action:
    service: notify.notify
    data:
      message: "Trading212 cash is low: {{ states('sensor.trading212_cash_available') }} {{ state_attr('sensor.trading212_cash_available', 'unit_of_measurement') }}"
```

---

### Top mover changed

Trigger whenever the top-performing position of the day changes.

```yaml
automation:
  alias: "Trading212 - Top Mover Changed"
  trigger:
    platform: state
    entity_id: sensor.trading212_top_daily_mover
  action:
    service: notify.notify
    data:
      message: "New top mover: {{ states('sensor.trading212_top_daily_mover') }}"
```
