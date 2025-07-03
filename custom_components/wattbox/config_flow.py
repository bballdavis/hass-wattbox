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
CONNECTION_TYPES = [
    "HTTP",
    "Telnet"
]
CONNECTION_TYPE_PORTS = {
    "HTTP": 80,
    "Telnet": 23,
}
HTTP_OPTIONS = [
    "audible_alarm", "auto_reboot", "battery_health", "battery_test", "cloud_status",
    "has_ups", "mute", "power_lost", "safe_voltage_status", "battery_charge",
    "battery_load", "current_value", "est_run_time", "power_value", "voltage_value"
]

def build_user_schema(user_input=None):
    # Default to Telnet
    connection_type = (user_input or {}).get("connection_type", "Telnet")
    # Always set port based on connection type
    if connection_type == "HTTP":
        port = 80
    else:
        port = 23
    schema = {
        vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
        vol.Required("connection_type", default=connection_type): vol.In(CONNECTION_TYPES),
        vol.Optional(CONF_PORT, default=port): cv.port,
        vol.Optional(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, DEFAULT_USER)): cv.string,
        vol.Optional(CONF_PASSWORD, default=(user_input or {}).get(CONF_PASSWORD, DEFAULT_PASSWORD)): cv.string,
        vol.Optional(CONF_NAME, default=(user_input or {}).get(CONF_NAME, DEFAULT_NAME)): cv.string,
    }
    if port == 80:
        # HTTP: show HTTP options, hide power monitoring
        for opt in HTTP_OPTIONS:
            schema[vol.Optional(opt, default=True)] = cv.boolean
    elif port == 23:
        # Telnet: show power monitoring
        schema[vol.Optional(CONF_ENABLE_POWER_SENSORS, default=(user_input or {}).get(CONF_ENABLE_POWER_SENSORS, DEFAULT_ENABLE_POWER_SENSORS))] = cv.boolean
    # SSH: no extra options
    return vol.Schema(schema)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Select API based on port
    connection_type = data.get("connection_type", "Telnet")
    port = int(data.get(CONF_PORT, CONNECTION_TYPE_PORTS[connection_type]))
    
    # Use HTTP API for port 80, Telnet API for others
    if connection_type == "HTTP" or port == 80:
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
    DOMAIN = DOMAIN
    """Handle a config flow for WattBox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Show all fields except connection type for reconfigure, else show connection type selector."""
        errors: dict[str, str] = {}
        # If this is a reconfigure context, skip connection type selection
        if self.context.get("reconfigure"):
            # Use the same logic as reconfigure step (see below)
            return await self.async_step_reconfigure(user_input)
        if user_input is not None:
            # Save connection type and move to next step
            self.connection_type = user_input["connection_type"]
            return await self.async_step_connection_details()
        # Only show connection type dropdown
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("connection_type", default="Telnet"): vol.In(CONNECTION_TYPES)
            }),
            errors=errors,
        )

    async def async_step_connection_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Show fields based on connection type, with translation references."""
        errors: dict[str, str] = {}
        connection_type = getattr(self, "connection_type", "Telnet")
        port = CONNECTION_TYPE_PORTS[connection_type]
        # Build schema for this connection type
        schema = {
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
            vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, port)): cv.port,
            vol.Optional(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, DEFAULT_USER)): cv.string,
            vol.Optional(CONF_PASSWORD, default=(user_input or {}).get(CONF_PASSWORD, DEFAULT_PASSWORD)): cv.string,
            vol.Optional(CONF_NAME, default=(user_input or {}).get(CONF_NAME, DEFAULT_NAME)): cv.string,
        }
        # Add HTTP or Telnet specific options
        if connection_type == "HTTP":
            for opt in HTTP_OPTIONS:
                schema[vol.Optional(opt, default=True)] = cv.boolean
        elif connection_type == "Telnet":
            schema[vol.Optional(CONF_ENABLE_POWER_SENSORS, default=(user_input or {}).get(CONF_ENABLE_POWER_SENSORS, DEFAULT_ENABLE_POWER_SENSORS))] = cv.boolean
        # No SSH
        if user_input is not None:
            # Merge connection type into user_input for validation
            user_input["connection_type"] = connection_type
            # Use the port the user entered, or the default for the connection type
            user_input[CONF_PORT] = user_input.get(CONF_PORT, port)
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["service_tag"])
                self._abort_if_unique_id_configured()
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
        # Use translation_key for step 2, matching the previous version of stage 1
        return self.async_show_form(
            step_id="connection_details",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={
                "default_username": DEFAULT_USER,
                "default_password": DEFAULT_PASSWORD,
                "default_port": str(port),
            },
            translation_key="user",  # Use the same translation key as the first step
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry. Do not allow changing connection type, and show correct sensor toggles."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        # Use the connection type from the existing entry
        connection_type = entry.data.get("connection_type", "Telnet")
        port = CONNECTION_TYPE_PORTS[connection_type]

        # Build schema for this connection type (no connection type selector)
        schema = {
            vol.Required(CONF_HOST, default=(user_input or entry.data or {}).get(CONF_HOST, "")): cv.string,
            vol.Required(CONF_PORT, default=(user_input or entry.data or {}).get(CONF_PORT, port)): cv.port,
            vol.Optional(CONF_USERNAME, default=(user_input or entry.data or {}).get(CONF_USERNAME, DEFAULT_USER)): cv.string,
            vol.Optional(CONF_PASSWORD, default=(user_input or entry.data or {}).get(CONF_PASSWORD, DEFAULT_PASSWORD)): cv.string,
            vol.Optional(CONF_NAME, default=(user_input or entry.data or {}).get(CONF_NAME, DEFAULT_NAME)): cv.string,
        }
        if connection_type == "HTTP":
            for opt in HTTP_OPTIONS:
                schema[vol.Optional(opt, default=(user_input or entry.data or {}).get(opt, True))] = cv.boolean
        elif connection_type == "Telnet":
            schema[vol.Optional(CONF_ENABLE_POWER_SENSORS, default=(user_input or entry.data or {}).get(CONF_ENABLE_POWER_SENSORS, DEFAULT_ENABLE_POWER_SENSORS))] = cv.boolean

        if user_input is not None:
            # Always use the original connection type
            user_input["connection_type"] = connection_type
            user_input[CONF_PORT] = user_input.get(CONF_PORT, port)
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

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(schema),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
