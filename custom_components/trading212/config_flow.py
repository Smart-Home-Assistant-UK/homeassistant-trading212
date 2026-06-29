from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import InvalidAPIKeyError, Trading212Client, APIConnectionError
from .const import (
    ALL_PIE_SENSORS,
    ALL_POSITION_SENSORS,
    CONF_API_SECRET,
    CONF_ENVIRONMENT,
    CONF_LABEL,
    CONF_PIE_SENSORS,
    CONF_POLL_INTERVAL,
    CONF_POSITION_SENSORS,
    DEFAULT_PIE_SENSORS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POSITION_SENSORS,
    DEMO_BASE_URL,
    DOMAIN,
    ENVIRONMENT_DEMO,
    ENVIRONMENT_LIVE,
    LIVE_BASE_URL,
    MIN_POLL_INTERVAL,
    OPTIONAL_PIE_SENSOR_OPTIONS,
    OPTIONAL_POSITION_SENSOR_OPTIONS,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_LABEL, default=""): str,
        vol.Required("api_key"): str,
        vol.Required(CONF_API_SECRET): str,
        vol.Required(CONF_ENVIRONMENT, default=ENVIRONMENT_LIVE): vol.In(
            [ENVIRONMENT_LIVE, ENVIRONMENT_DEMO]
        ),
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
    }
)

_POSITION_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[{"value": k, "label": v} for k, v in OPTIONAL_POSITION_SENSOR_OPTIONS.items()],
        multiple=True,
        mode=SelectSelectorMode.LIST,
    )
)

_PIE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[{"value": k, "label": v} for k, v in OPTIONAL_PIE_SENSOR_OPTIONS.items()],
        multiple=True,
        mode=SelectSelectorMode.LIST,
    )
)

SENSORS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_POSITION_SENSORS, default=DEFAULT_POSITION_SENSORS): _POSITION_SELECTOR,
        vol.Optional(CONF_PIE_SENSORS, default=DEFAULT_PIE_SENSORS): _PIE_SELECTOR,
    }
)


def _options_schema(
    current_label: str,
    current_env: str,
    current_interval: int,
    current_position_sensors: list[str],
    current_pie_sensors: list[str],
) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_LABEL, default=current_label): str,
            vol.Required(CONF_ENVIRONMENT, default=current_env): vol.In(
                [ENVIRONMENT_LIVE, ENVIRONMENT_DEMO]
            ),
            vol.Required(CONF_POLL_INTERVAL, default=current_interval): int,
            vol.Optional("sensor_selection"): section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_POSITION_SENSORS,
                            default=current_position_sensors,
                        ): _POSITION_SELECTOR,
                        vol.Optional(
                            CONF_PIE_SENSORS,
                            default=current_pie_sensors,
                        ): _PIE_SELECTOR,
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


class Trading212ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL) < MIN_POLL_INTERVAL:
                errors[CONF_POLL_INTERVAL] = "invalid_poll_interval"
                return self.async_show_form(
                    step_id="user", data_schema=USER_SCHEMA, errors=errors
                )

            base_url = (
                LIVE_BASE_URL
                if user_input[CONF_ENVIRONMENT] == ENVIRONMENT_LIVE
                else DEMO_BASE_URL
            )
            session = async_get_clientsession(self.hass)
            client = Trading212Client(
                session,
                user_input["api_key"],
                base_url,
                api_secret=user_input.get(CONF_API_SECRET),
            )
            try:
                summary = await client.get_account_summary()
            except InvalidAPIKeyError:
                errors["api_key"] = "invalid_auth"
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                account_id = str(summary.get("id", ""))
                unique_id = f"{account_id}_{user_input[CONF_ENVIRONMENT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                self._user_input = {**user_input, "_account_id": account_id}
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_sensors(self, user_input=None):
        if user_input is not None:
            data = {**self._user_input}
            data.pop("_account_id", None)
            data[CONF_POSITION_SENSORS] = user_input.get(CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS)
            data[CONF_PIE_SENSORS] = user_input.get(CONF_PIE_SENSORS, DEFAULT_PIE_SENSORS)
            env = data[CONF_ENVIRONMENT].title()
            label = data.get(CONF_LABEL, "").strip()
            title = f"Trading212 – {label} ({env})" if label else f"Trading212 ({env})"
            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="sensors",
            data_schema=SENSORS_SCHEMA,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return Trading212OptionsFlow(config_entry)


class Trading212OptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL) < MIN_POLL_INTERVAL:
                errors[CONF_POLL_INTERVAL] = "invalid_poll_interval"
            else:
                # Unwrap the collapsible section into flat storage
                sensor_section = user_input.pop("sensor_selection", None) or {}
                user_input[CONF_POSITION_SENSORS] = sensor_section.get(CONF_POSITION_SENSORS, DEFAULT_POSITION_SENSORS)
                user_input[CONF_PIE_SENSORS] = sensor_section.get(CONF_PIE_SENSORS, DEFAULT_PIE_SENSORS)
                return self.async_create_entry(title="", data=user_input)

        combined = {**self._config_entry.data, **self._config_entry.options}
        # Key absent = pre-feature install; show all ticked to reflect what was actually created
        current_position_sensors = combined[CONF_POSITION_SENSORS] if CONF_POSITION_SENSORS in combined else ALL_POSITION_SENSORS
        current_pie_sensors = combined[CONF_PIE_SENSORS] if CONF_PIE_SENSORS in combined else ALL_PIE_SENSORS
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                current_label=combined.get(CONF_LABEL, ""),
                current_env=combined.get(CONF_ENVIRONMENT, ENVIRONMENT_LIVE),
                current_interval=combined.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                current_position_sensors=current_position_sensors,
                current_pie_sensors=current_pie_sensors,
            ),
            errors=errors,
        )
