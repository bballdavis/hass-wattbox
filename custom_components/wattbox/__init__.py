"""
Component to integrate with wattbox.

For more details about this component, please refer to
https://github.com/bballdavis/hass-wattbox/
"""
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed  # type: ignore

from .const import DOMAIN

# Import API library components directly
from .pywattbox_800.client import WattBoxClient
from .pywattbox_800.exceptions import WattBoxConnectionError, WattBoxError
from .api_wrapper import PyWattBoxWrapper

_LOGGER = logging.getLogger(__name__)

PLATFORMS: List[str] = ["sensor", "switch", "binary_sensor"]


class WattBoxUpdateCoordinator(DataUpdateCoordinator):
    """WattBox data update coordinator."""

    def __init__(self, hass: HomeAssistant, client: WattBoxClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.client = client
        self.device_info = None
        # Cache for outlet power info to avoid excessive API calls
        self._power_cache = {}
        self._power_cache_expire = 10  # Cache for 10 seconds

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from WattBox."""
        try:
            # Ensure we're connected before attempting to fetch data
            if not self.client.is_connected():
                _LOGGER.info("Reconnecting to WattBox device")
                await self.hass.async_add_executor_job(self.client.connect)
            
            _LOGGER.debug("Fetching device info from WattBox")
            # Run the blocking calls in the executor
            device_info = await self.hass.async_add_executor_job(
                self.client.get_device_info, True  # Force refresh
            )
            
            outlet_count = len(device_info.outlets) if device_info.outlets else 0
            _LOGGER.info(f"Successfully updated WattBox data: {outlet_count} outlets, power_status: {device_info.power_status is not None}")
            
            return {
                "device_info": device_info,
                "outlets": device_info.outlets,
                "system_info": device_info.system_info,
                "power_status": device_info.power_status,
                "ups_status": device_info.ups_status,
                "ups_connected": device_info.ups_connected,
                "auto_reboot_enabled": device_info.auto_reboot_enabled,
            }
            
        except WattBoxConnectionError as err:
            # Try to reconnect once on connection error
            try:
                await self.hass.async_add_executor_job(self.client.connect)
                device_info = await self.hass.async_add_executor_job(
                    self.client.get_device_info, True
                )
                return {
                    "device_info": device_info,
                    "outlets": device_info.outlets,
                    "system_info": device_info.system_info,
                    "power_status": device_info.power_status,
                    "ups_status": device_info.ups_status,
                    "ups_connected": device_info.ups_connected,
                    "auto_reboot_enabled": device_info.auto_reboot_enabled,
                }
            except Exception as reconnect_err:
                raise UpdateFailed(f"Error communicating with WattBox after reconnect: {reconnect_err}")
        except (WattBoxError, ValueError) as err:
            # Handle parsing errors more gracefully
            _LOGGER.warning(f"Error updating WattBox data: {err}")
            raise UpdateFailed(f"Error updating WattBox data: {err}")
        except Exception as err:
            # Catch all other errors
            _LOGGER.error(f"Unexpected error updating WattBox data: {err}")
            raise UpdateFailed(f"Unexpected error updating WattBox data: {err}")

    async def get_outlet_power_info(self, outlet_index: int) -> Dict[str, Any]:
        """Get power info for a specific outlet with caching."""
        current_time = time.time()
        cache_key = f"outlet_{outlet_index}"
        
        # Check if we have cached data that's still valid
        if (cache_key in self._power_cache and 
            current_time - self._power_cache[cache_key]["timestamp"] < self._power_cache_expire):
            _LOGGER.debug(f"Using cached power info for outlet {outlet_index}")
            return self._power_cache[cache_key]["data"]
        
        # Fetch fresh data
        try:
            _LOGGER.debug(f"Fetching fresh power info for outlet {outlet_index}")
            power_info = await self.hass.async_add_executor_job(
                self.client.get_outlet_power_status, outlet_index
            )
            
            if power_info:
                result = {
                    "power_watts": power_info.power_watts,
                    "current_amps": power_info.current_amps, 
                    "voltage_volts": power_info.voltage_volts
                }
                _LOGGER.info(f"Retrieved power data for outlet {outlet_index}: {result}")
            else:
                # Device doesn't support individual outlet power monitoring
                _LOGGER.info(f"Individual outlet power monitoring not supported for outlet {outlet_index}")
                result = {
                    "power_watts": None,
                    "current_amps": None,
                    "voltage_volts": None
                }
            
            # Cache the result
            self._power_cache[cache_key] = {
                "data": result,
                "timestamp": current_time
            }
            
            return result
            
        except Exception as err:
            _LOGGER.warning(f"Failed to get power info for outlet {outlet_index}: {err}")
            # Return None values if we can't get power info
            return {
                "power_watts": None,
                "current_amps": None,
                "voltage_volts": None
            }

    def get_master_switch_state(self) -> Optional[bool]:
        """Get the current state of the master switch based on outlet states."""
        if not self.data or not self.data.get("outlets"):
            return None
            
        # Return True if any outlet is on
        for outlet in self.data["outlets"]:
            if outlet.status:
                return True
        return False
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WattBox from a config entry."""
    _LOGGER.info("=== WattBox Integration: Starting setup ===")
    
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 23)
    username = entry.data.get(CONF_USERNAME, "wattbox")
    password = entry.data.get(CONF_PASSWORD, "wattbox")

    _LOGGER.info(f"WattBox Integration: Connecting to {host}:{port}")

    # Create the client based on port (same logic as config flow)
    if port == 80:
        client = PyWattBoxWrapper(
            host,
            username,
            password,
            port=port,
        )
    else:
        client = WattBoxClient(
            host=host,
            port=port,
            username=username,
            password=password,
            timeout=10.0
        )

    # Test the connection
    try:
        _LOGGER.info("Connecting to WattBox at %s:%s", host, port)
        await hass.async_add_executor_job(client.connect)
        # Only ping for non-HTTP clients (HTTP wrapper doesn't support ping)
        if port != 80:
            await hass.async_add_executor_job(client.ping)
        _LOGGER.info("Successfully connected to WattBox at %s", host)
        # Don't disconnect - let the coordinator manage the connection
    except WattBoxError as err:
        _LOGGER.error("Failed to connect to WattBox at %s: %s", host, err)
        raise ConfigEntryNotReady from err
    except Exception as err:
        _LOGGER.error("Unexpected error connecting to WattBox at %s: %s", host, err)
        raise ConfigEntryNotReady from err

    # Create the coordinator
    coordinator = WattBoxUpdateCoordinator(hass, client)

    # Fetch initial data
    _LOGGER.info("Fetching initial device data from WattBox")
    await coordinator.async_config_entry_first_refresh()
    
    # Log some basic info about the device
    if coordinator.data and coordinator.data.get("system_info"):
        system_info = coordinator.data["system_info"]
        outlet_count = len(coordinator.data.get("outlets", []))
        _LOGGER.info("WattBox device initialized: Model=%s, Firmware=%s, Outlets=%d", 
                    system_info.model, system_info.firmware, outlet_count)

    # Store the coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        # Disconnect the client
        try:
            await hass.async_add_executor_job(coordinator.client.disconnect)
        except Exception as err:
            _LOGGER.debug("Error disconnecting from WattBox: %s", err)

    return unload_ok
