"""Config flow for WattBox integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol # type: ignore
from homeassistant import config_entries, core, exceptions  # type: ignore
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT, CONF_USERNAME  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.data_entry_flow import FlowResult  # type: ignore
import homeassistant.helpers.config_validation as cv  # type: ignore

from .const import (
    DOMAIN, 
    DEFAULT_NAME, 
    DEFAULT_PASSWORD, 
    DEFAULT_PORT, 
    DEFAULT_USER,
    CONF_ENABLE_POWER_SENSORS,
    DEFAULT_ENABLE_POWER_SENSORS,
)

# Import API library components directly

# API wrappers
from .pywattbox_800.client import WattBoxClient
from .pywattbox_800.exceptions import (
    WattBoxConnectionError,
    WattBoxAuthenticationError,
    WattBoxError,
)
from .api_wrapper import PyWattBoxWrapper

_LOGGER = logging.getLogger(__name__)

# Data schema for user input

# Connection type dropdown and HTTP options
CONNECTION_TYPES = {
    "HTTP (80)": 80,
    "Telnet (23)": 23,
    "SSH (22)": 22,
}
HTTP_OPTIONS = [
    "audible_alarm", "auto_reboot", "battery_health", "battery_test", "cloud_status",
    "has_ups", "mute", "power_lost", "safe_voltage_status", "battery_charge",
    "battery_load", "current_value", "est_run_time", "power_value", "voltage_value"
]

def build_user_schema(user_input=None):
    connection_type = (user_input or {}).get("connection_type", "HTTP (80)")
    port = CONNECTION_TYPES[connection_type]
    if port == 80:
        # HTTP: show HTTP options, hide power monitoring
        schema = {
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
            vol.Required("connection_type", default=connection_type): vol.In(CONNECTION_TYPES),
            vol.Optional(CONF_PORT, default=80): cv.port,
            vol.Optional(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, DEFAULT_USER)): cv.string,
            vol.Optional(CONF_PASSWORD, default=(user_input or {}).get(CONF_PASSWORD, DEFAULT_PASSWORD)): cv.string,
            vol.Optional(CONF_NAME, default=(user_input or {}).get(CONF_NAME, DEFAULT_NAME)): cv.string,
        }
        for opt in HTTP_OPTIONS:
            schema[vol.Optional(opt, default=True)] = cv.boolean
        return vol.Schema(schema)
    else:
        # Telnet/SSH: show power monitoring
        return vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
            vol.Required("connection_type", default=connection_type): vol.In(CONNECTION_TYPES),
            vol.Optional(CONF_PORT, default=port): cv.port,
            vol.Optional(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, DEFAULT_USER)): cv.string,
            vol.Optional(CONF_PASSWORD, default=(user_input or {}).get(CONF_PASSWORD, DEFAULT_PASSWORD)): cv.string,
            vol.Optional(CONF_NAME, default=(user_input or {}).get(CONF_NAME, DEFAULT_NAME)): cv.string,
            vol.Optional(CONF_ENABLE_POWER_SENSORS, default=(user_input or {}).get(CONF_ENABLE_POWER_SENSORS, DEFAULT_ENABLE_POWER_SENSORS)): cv.boolean,
        })


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Select API based on port
    port = data.get(CONF_PORT, 80)
    if port == 80:
        client = PyWattBoxWrapper(
            data[CONF_HOST],
            data.get(CONF_USERNAME, DEFAULT_USER),
            data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
            port=port,
        )
    else:
        client = WattBoxClient(
            host=data[CONF_HOST],
            port=port,
            username=data.get(CONF_USERNAME, DEFAULT_USER),
            password=data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
            timeout=10.0,
        )

    try:
        # Test connection and get device info
        await hass.async_add_executor_job(client.connect)
        # Get device information for validation and unique ID
        system_info = await hass.async_add_executor_job(client.get_system_info)
        # Disconnect after testing
        await hass.async_add_executor_job(client.disconnect)
        # Return info that you want to store in the config entry.
        return {
            "title": f"WattBox {system_info['model'] if isinstance(system_info, dict) else system_info.model}",
            "model": system_info['model'] if isinstance(system_info, dict) else system_info.model,
            "firmware": system_info['firmware'] if isinstance(system_info, dict) else system_info.firmware,
            "hostname": system_info['hostname'] if isinstance(system_info, dict) else system_info.hostname,
            "service_tag": system_info.get('serial_number') if isinstance(system_info, dict) else getattr(system_info, 'service_tag', None),
            "outlet_count": system_info['outlet_count'] if isinstance(system_info, dict) else system_info.outlet_count,
        }
    except WattBoxConnectionError as err:
        _LOGGER.error("Connection error: %s", err)
        raise CannotConnect from err
    except WattBoxAuthenticationError as err:
        _LOGGER.error("Authentication error: %s", err)
        raise InvalidAuth from err
    except WattBoxError as err:
        _LOGGER.error("WattBox error: %s", err)
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.error("Unexpected error: %s", err)
        raise CannotConnect from err
    finally:
        # Ensure client is disconnected
        try:
            await hass.async_add_executor_job(client.disconnect)
        except Exception:
            pass


class ConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for WattBox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured (by service tag)
                await self.async_set_unique_id(info["service_tag"])
                self._abort_if_unique_id_configured()
                # Create the config entry
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                    description_placeholders={
                        "model": info["model"],
                        "firmware": info["firmware"],
                        "hostname": info["hostname"],
                        "outlet_count": str(info["outlet_count"]),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=build_user_schema(user_input),
            errors=errors,
            description_placeholders={
                "default_username": DEFAULT_USER,
                "default_password": DEFAULT_PASSWORD,
                "default_port": str(DEFAULT_PORT),
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Update the config entry
                return self.async_update_reload_and_abort(
                    entry, data=user_input, reason="reconfigure_successful"
                )
        else:
            # Pre-fill with existing data
            user_input = entry.data if entry.data is not None else {}

        # Use the same dynamic schema as the user step
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=build_user_schema(user_input),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
