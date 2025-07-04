"""Switch platform for wattbox."""

import asyncio
import logging
import time
from typing import Any, Optional

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore
from homeassistant.exceptions import ServiceValidationError  # type: ignore

from .const import DOMAIN, get_outlet_device_info, get_wattbox_device_info, canonicalize_name, friendly_name, get_outlet_device_info_canonical, get_wattbox_device_info_canonical, unique_wattbox_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WattBox switch platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    entry_id = entry.entry_id
    
    # --- Dynamic entity setup based on API type ---
    # For HTTP API (pywattbox), only create switch per outlet, using outlet_status for outlet count.
    # For v2.4 API, retain existing dynamic logic.
    # See: custom_components/wattbox/pywattbox/wattbox_api_v2.0.md for HTTP API fields
    # See: custom_components/wattbox/pywattbox_800/README.md for v2.4 API fields

    client = getattr(coordinator, "client", None)
    is_http_api = client and client.__class__.__name__ in ("PyWattBoxWrapper", "HttpWattBox")

    main_device_name = entry.data.get("name") or entry.title or "wattbox"
    canonical_main_device = canonicalize_name(main_device_name)

    # Master switch (system device)
    entities.append(WattBoxMasterSwitch(coordinator, canonical_main_device, friendly_name(main_device_name, sensor_type="Master Switch"), entry_id=entry_id))

    # Individual outlet switches
    if coordinator.data and coordinator.data.get("outlets"):
        for outlet in coordinator.data["outlets"]:
            switch_name = friendly_name(main_device_name, outlet.index, "Switch")
            entities.append(WattBoxOutletSwitch(coordinator, canonical_main_device, outlet.index, outlet.name, switch_name, entry_id=entry_id))
    async_add_entities(entities)


class WattBoxBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for WattBox switches."""

    def __init__(self, coordinator, main_device: str, unique_id: str, name: str, entry_id: Optional[str] = None):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, unique_id)
        self._attr_name = name
        self._attr_device_class = SwitchDeviceClass.OUTLET

    @property
    def device_info(self):
        """Return device information for main WattBox device."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        return get_wattbox_device_info_canonical(self._main_device, system_info)


class WattBoxOutletSwitch(CoordinatorEntity, SwitchEntity):
    """WattBox outlet switch."""

    def __init__(self, coordinator, main_device: str, outlet_index: int, outlet_name: str, name: str, entry_id: Optional[str] = None):
        """Initialize the outlet switch."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._outlet_index = outlet_index
        self._outlet_name = outlet_name
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, f"outlet_{outlet_index}", "switch")
        # Compose friendly name as "<Main Device> <Outlet Name> Switch"
        self._attr_name = f"{main_device.replace('_', ' ').title()} {outlet_name} Switch"
        self._attr_device_class = SwitchDeviceClass.OUTLET
        
        # Cooldown mechanism
        self._last_operation_time = 0
        self._cooldown_period = 5   # Reduced to 5 seconds cooldown
        self._operation_delay = 2   # Reduced to 2 second delay to check if changes took effect

    @property
    def device_info(self):
        """Return device information for this outlet device, using the main device and outlet name as the device name."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        device_name = f"{self._main_device.replace('_', ' ').title()} {self._outlet_name}" if self._outlet_name else self._main_device.replace('_', ' ').title()
        return get_outlet_device_info_canonical(self._main_device, self._outlet_index, system_info, device_name=device_name)

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if outlet is on."""
        if not self.coordinator.data or not self.coordinator.data.get("outlets"):
            return None
            
        for outlet in self.coordinator.data["outlets"]:
            if outlet.index == self._outlet_index:
                return outlet.status
        return None

    def _is_in_cooldown(self) -> bool:
        """Check if the switch is in cooldown period."""
        current_time = time.time()
        return (current_time - self._last_operation_time) < self._cooldown_period

    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds."""
        current_time = time.time()
        elapsed = current_time - self._last_operation_time
        remaining = self._cooldown_period - elapsed
        return max(0, remaining)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.coordinator.data.get("outlets"):
            return {}
            
        for outlet in self.coordinator.data["outlets"]:
            if outlet.index == self._outlet_index:
                attrs = {
                    "outlet_index": outlet.index,
                    "outlet_name": outlet.name,
                }
                # Only add power attributes if they are available and not None
                if outlet.power_watts is not None:
                    attrs["power_watts"] = outlet.power_watts
                if outlet.current_amps is not None:
                    attrs["current_amps"] = outlet.current_amps
                if outlet.voltage_volts is not None:
                    attrs["voltage_volts"] = outlet.voltage_volts
                return attrs
        return {}

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the outlet on."""
        # Check cooldown period
        if self._is_in_cooldown():
            remaining = self._get_cooldown_remaining()
            raise ServiceValidationError(
                f"Outlet {self._outlet_index} is in cooldown period. "
                f"Please wait {remaining:.1f} more seconds."
            )
        
        try:
            success = await self.hass.async_add_executor_job(
                self.coordinator.client.turn_on_outlet, self._outlet_index
            )
            if success:
                _LOGGER.debug("Successfully turned on outlet %s", self._outlet_index)
                # Update last operation time for cooldown
                self._last_operation_time = time.time()
                
                # Longer delay to let the device process the command
                await asyncio.sleep(self._operation_delay)
                
                # Request a coordinator refresh to update all related entities
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn on outlet %s", self._outlet_index)
        except Exception as err:
            _LOGGER.error("Error turning on outlet %s: %s", self._outlet_index, err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the outlet off."""
        # Check cooldown period
        if self._is_in_cooldown():
            remaining = self._get_cooldown_remaining()
            raise ServiceValidationError(
                f"Outlet {self._outlet_index} is in cooldown period. "
                f"Please wait {remaining:.1f} more seconds."
            )
        
        try:
            success = await self.hass.async_add_executor_job(
                self.coordinator.client.turn_off_outlet, self._outlet_index
            )
            if success:
                _LOGGER.debug("Successfully turned off outlet %s", self._outlet_index)
                # Update last operation time for cooldown
                self._last_operation_time = time.time()
                
                # Longer delay to let the device process the command
                await asyncio.sleep(self._operation_delay)
                
                # Request a coordinator refresh to update all related entities
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn off outlet %s", self._outlet_index)
        except Exception as err:
            _LOGGER.error("Error turning off outlet %s: %s", self._outlet_index, err)


class WattBoxMasterSwitch(WattBoxBaseSwitch):
    """WattBox master switch (controls all outlets)."""

    def __init__(self, coordinator, main_device: str, name: str, entry_id: Optional[str] = None):
        """Initialize the master switch."""
        super().__init__(coordinator, main_device, "master", name, entry_id=entry_id)
        
        # Cooldown mechanism
        self._last_operation_time = 0
        self._cooldown_period = 5   # Reduced to 5 seconds cooldown
        self._operation_delay = 2   # Reduced to 2 second delay to check if changes took effect

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if any outlet is on."""
        # Use coordinator's centralized state management
        return self.coordinator.get_master_switch_state()

    def _is_in_cooldown(self) -> bool:
        """Check if the master switch is in cooldown period."""
        current_time = time.time()
        return (current_time - self._last_operation_time) < self._cooldown_period

    def _get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds."""
        current_time = time.time()
        elapsed = current_time - self._last_operation_time
        remaining = self._cooldown_period - elapsed
        return max(0, remaining)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or not self.coordinator.data.get("outlets"):
            return {}
            
        total_outlets = len(self.coordinator.data["outlets"])
        on_outlets = sum(1 for outlet in self.coordinator.data["outlets"] if outlet.status)
        
        return {
            "total_outlets": total_outlets,
            "outlets_on": on_outlets,
            "outlets_off": total_outlets - on_outlets,
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Turn all outlets on."""
        # Check cooldown period
        if self._is_in_cooldown():
            remaining = self._get_cooldown_remaining()
            raise ServiceValidationError(
                f"Master switch is in cooldown period. "
                f"Please wait {remaining:.1f} more seconds."
            )
        
        try:
            # Turn on all outlets individually
            if self.coordinator.data and self.coordinator.data.get("outlets"):
                for outlet in self.coordinator.data["outlets"]:
                    if not outlet.status:  # Only turn on if currently off
                        await self.hass.async_add_executor_job(
                            self.coordinator.client.turn_on_outlet, outlet.index
                        )
                        # Small delay between commands to avoid API issues
                        await asyncio.sleep(0.1)
                
                _LOGGER.debug("Successfully turned on all outlets")
                # Update last operation time for cooldown
                self._last_operation_time = time.time()
                
                # Longer delay to let the device process the commands
                await asyncio.sleep(self._operation_delay)
                
                # Trigger a coordinator refresh to update all outlet states
                await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Error turning on all outlets: %s", err)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn all outlets off."""
        # Check cooldown period
        if self._is_in_cooldown():
            remaining = self._get_cooldown_remaining()
            raise ServiceValidationError(
                f"Master switch is in cooldown period. "
                f"Please wait {remaining:.1f} more seconds."
            )
        
        try:
            # Use the reset all outlets command (outlet 0)
            success = await self.hass.async_add_executor_job(
                self.coordinator.client.turn_off_outlet, 0  # 0 = all outlets
            )
            if success:
                _LOGGER.debug("Successfully turned off all outlets")
                # Update last operation time for cooldown
                self._last_operation_time = time.time()
                
                # Longer delay to let the device process the command
                await asyncio.sleep(self._operation_delay)
                
                # Trigger a coordinator refresh to update all outlet states
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to turn off all outlets")
        except Exception as err:
            _LOGGER.error("Error turning off all outlets: %s", err)
