from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvalidAPIKeyError, Trading212Client, APIConnectionError
from .const import (
    CONF_API_SECRET,
    CONF_ENVIRONMENT,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEMO_BASE_URL,
    DOMAIN,
    ENVIRONMENT_DEMO,
    ENVIRONMENT_LIVE,
    LIVE_BASE_URL,
    MIN_POLL_INTERVAL,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required("api_key"): str,
        vol.Required(CONF_API_SECRET): str,
        vol.Required(CONF_ENVIRONMENT, default=ENVIRONMENT_LIVE): vol.In(
            [ENVIRONMENT_LIVE, ENVIRONMENT_DEMO]
        ),
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
    }
)


class Trading212ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Manual range check — keeps schema simple so HA doesn't raise
            # InvalidData before our handler can return a friendly form error.
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
                env = user_input[CONF_ENVIRONMENT].title()
                return self.async_create_entry(
                    title=f"Trading212 ({env})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
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
                return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        current_env = self._config_entry.data.get(CONF_ENVIRONMENT, ENVIRONMENT_LIVE)
        schema = vol.Schema(
            {
                vol.Required(CONF_ENVIRONMENT, default=current_env): vol.In(
                    [ENVIRONMENT_LIVE, ENVIRONMENT_DEMO]
                ),
                vol.Required(CONF_POLL_INTERVAL, default=current_interval): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
