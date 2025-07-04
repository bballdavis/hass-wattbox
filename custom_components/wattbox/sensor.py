"""Sensor platform for wattbox."""

import logging
import time
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import (  # type: ignore
    UnitOfPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import (
    DOMAIN, 
    OUTLET_SENSOR_TYPES, 
    get_outlet_device_info, 
    get_wattbox_device_info,
    CONF_ENABLE_POWER_SENSORS,
    DEFAULT_ENABLE_POWER_SENSORS,
    canonicalize_name,
    friendly_name,
    get_outlet_device_info_canonical,
    get_wattbox_device_info_canonical,
    unique_wattbox_entity_id,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WattBox sensor platform."""
    _LOGGER.info("=== WattBox Sensor Platform: Starting setup ===")
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entry_id = entry.entry_id

    # Check if power monitoring is enabled in config
    enable_power_sensors = entry.data.get(CONF_ENABLE_POWER_SENSORS, DEFAULT_ENABLE_POWER_SENSORS)
    _LOGGER.info(f"Setting up WattBox sensors (power monitoring: {'enabled' if enable_power_sensors else 'disabled'})")
    _LOGGER.debug(f"Power sensors enabled: {enable_power_sensors}")
    
    entities = []
    
    client = getattr(coordinator, "client", None)
    is_http_api = client and client.__class__.__name__ in ("PyWattBoxWrapper", "HttpWattBox")

    # Get the main device name from config entry (user-defined or fallback)
    main_device_name = entry.data.get("name") or entry.title or "wattbox"
    canonical_main_device = canonicalize_name(main_device_name)
    # Track used device names to avoid duplicates
    used_device_names = set()
    base_device_name = main_device_name
    increment = 1
    while main_device_name in used_device_names:
        increment += 1
        main_device_name = f"{base_device_name}_{increment}"
    used_device_names.add(main_device_name)

    # System sensors (always create these)
    entities.extend([
        WattBoxSystemSensor(coordinator, canonical_main_device, "firmware", "Firmware", entry_id=entry_id),
        WattBoxSystemSensor(coordinator, canonical_main_device, "model", "Model", entry_id=entry_id),
        WattBoxSystemSensor(coordinator, canonical_main_device, "hostname", "Hostname", entry_id=entry_id),
        WattBoxSystemSensor(coordinator, canonical_main_device, "service_tag", "Service Tag", entry_id=entry_id),
        WattBoxSystemSensor(coordinator, canonical_main_device, "outlet_count", "Outlet Count", entry_id=entry_id),
    ])

    # Power/UPS sensors (only if available and enabled)
    if not is_http_api:
        # v2.4 API: retain existing dynamic logic
        if enable_power_sensors and coordinator.data and coordinator.data.get("power_status"):
            entities.extend([
                WattBoxPowerSensor(coordinator, canonical_main_device, "voltage", "Voltage", UnitOfElectricPotential.VOLT, entry_id=entry_id),
                WattBoxPowerSensor(coordinator, canonical_main_device, "current", "Current", UnitOfElectricCurrent.AMPERE, entry_id=entry_id),
                WattBoxPowerSensor(coordinator, canonical_main_device, "power", "Power", UnitOfPower.WATT, entry_id=entry_id),
            ])
        if coordinator.data and coordinator.data.get("ups_connected"):
            entities.extend([
                WattBoxUPSSensor(coordinator, "battery_level", "UPS Battery Level", PERCENTAGE),
                WattBoxUPSSensor(coordinator, "runtime_remaining", "UPS Runtime Remaining"),
                WattBoxUPSSensor(coordinator, "status", "UPS Status"),
            ])
    else:
        # HTTP API: Only create power sensors if present in wattbox_info.xml
        if enable_power_sensors and coordinator.data and coordinator.data.get("power_status"):
            ps = coordinator.data["power_status"]
            if getattr(ps, "voltage_volts", None) is not None:
                entities.append(WattBoxPowerSensor(coordinator, canonical_main_device, "voltage", "Voltage", UnitOfElectricPotential.VOLT, entry_id=entry_id))
            if getattr(ps, "current_amps", None) is not None:
                entities.append(WattBoxPowerSensor(coordinator, canonical_main_device, "current", "Current", UnitOfElectricCurrent.AMPERE, entry_id=entry_id))
            if getattr(ps, "power_watts", None) is not None:
                entities.append(WattBoxPowerSensor(coordinator, canonical_main_device, "power", "Power", UnitOfPower.WATT, entry_id=entry_id))
        # UPS sensors: only if present
        if coordinator.data and coordinator.data.get("ups_status"):
            ups = coordinator.data["ups_status"]
            if getattr(ups, "battery_charge", None) is not None:
                entities.append(WattBoxUPSSensor(coordinator, "battery_level", "UPS Battery Level", PERCENTAGE))
            if getattr(ups, "battery_runtime", None) is not None:
                entities.append(WattBoxUPSSensor(coordinator, "runtime_remaining", "UPS Runtime Remaining"))
            if getattr(ups, "battery_health", None) is not None:
                entities.append(WattBoxUPSSensor(coordinator, "status", "UPS Status"))

    # Outlet sensors
    if coordinator.data and coordinator.data.get("outlets"):
        outlet_count = len(coordinator.data['outlets'])
        _LOGGER.info(f"Creating sensors for {outlet_count} outlets")
        for outlet in coordinator.data["outlets"]:
            if is_http_api:
                sensor_name = friendly_name(main_device_name, outlet.index, "Status")
                entities.append(WattBoxOutletSensor(
                    coordinator, canonical_main_device, outlet.index, outlet.name, "status", sensor_name, None, None, entry_id=entry_id
                ))
            else:
                if enable_power_sensors:
                    _LOGGER.info(f"Creating power sensors for outlet {outlet.index} ({outlet.name})")
                    for sensor_type, sensor_config in OUTLET_SENSOR_TYPES.items():
                        sensor_name = friendly_name(main_device_name, outlet.index, sensor_type)
                        entities.append(WattBoxOutletSensor(
                            coordinator, canonical_main_device, outlet.index, outlet.name, sensor_type, 
                            sensor_name, sensor_config["unit"], sensor_config["icon"], entry_id=entry_id
                        ))
                else:
                    _LOGGER.info(f"Power sensors disabled, skipping outlet {outlet.index}")

    _LOGGER.info(f"Successfully created {len(entities)} WattBox sensors")
    async_add_entities(entities)


class WattBoxBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for WattBox sensors."""

    def __init__(self, coordinator, main_device: str, sensor_type: str, name: str, unit: Optional[str] = None, entry_id: Optional[str] = None):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._sensor_type = sensor_type
        self._attr_name = name
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, sensor_type)
        if unit:
            self._attr_native_unit_of_measurement = unit

    @property
    def device_info(self):
        """Return device information for main WattBox device."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        return get_wattbox_device_info_canonical(self._main_device, system_info)


class WattBoxSystemSensor(WattBoxBaseSensor):
    """System information sensor."""

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data or not self.coordinator.data.get("system_info"):
            return None
            
        system_info = self.coordinator.data["system_info"]
        return getattr(system_info, self._sensor_type, None)


class WattBoxPowerSensor(WattBoxBaseSensor):
    """Power status sensor."""

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class."""
        if self._sensor_type == "voltage":
            return SensorDeviceClass.VOLTAGE
        elif self._sensor_type == "current":
            return SensorDeviceClass.CURRENT
        elif self._sensor_type == "power":
            return SensorDeviceClass.POWER
        return None

    @property
    def suggested_display_precision(self) -> Optional[int]:
        """Return the suggested display precision for this sensor."""
        if self._sensor_type == "current":
            return 2  # 2 decimal places for current
        elif self._sensor_type in ["power", "voltage"]:
            return 0  # 0 decimal places for power and voltage
        return None

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data or not self.coordinator.data.get("power_status"):
            return None
            
        power_status = self.coordinator.data["power_status"]
        
        # Return raw values without rounding - let Home Assistant handle display precision
        if self._sensor_type == "current":
            return power_status.current_amps
        elif self._sensor_type == "power":
            return power_status.power_watts
        elif self._sensor_type == "voltage":
            return power_status.voltage_volts
        
        return None


class WattBoxUPSSensor(WattBoxBaseSensor):
    """UPS status sensor."""

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class."""
        if self._sensor_type == "battery_level":
            return SensorDeviceClass.BATTERY
        return None

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data or not self.coordinator.data.get("ups_status"):
            return None
            
        ups_status = self.coordinator.data["ups_status"]
        return getattr(ups_status, self._sensor_type, None)


class WattBoxOutletSensor(CoordinatorEntity, SensorEntity):
    """Outlet-specific sensor."""

    def __init__(self, coordinator, main_device: str, outlet_index: int, outlet_name: str, sensor_type: str, sensor_name: str, unit: Optional[str] = None, icon: Optional[str] = None, entry_id: Optional[str] = None):
        """Initialize the outlet sensor."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._outlet_index = outlet_index
        self._outlet_name = outlet_name
        self._sensor_type = sensor_type
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, f"outlet_{outlet_index}", sensor_type)
        # Compose friendly name as "<Main Device> <Outlet Name> <Sensor Type>"
        self._attr_name = f"{main_device.replace('_', ' ').title()} {outlet_name} {sensor_type.title()}"
        if unit:
            self._attr_native_unit_of_measurement = unit
        if icon:
            self._attr_icon = icon
        # Cache for power data
        self._cached_power_data = None
        self._last_power_update = 0

    @property
    def device_info(self):
        """Return device information for this outlet device, using the main device and outlet name as the device name."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        device_name = f"{self._main_device.replace('_', ' ').title()} {self._outlet_name}" if self._outlet_name else self._main_device.replace('_', ' ').title()
        return get_outlet_device_info_canonical(self._main_device, self._outlet_index, system_info, device_name=device_name)

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class."""
        if self._sensor_type == "power":
            return SensorDeviceClass.POWER
        elif self._sensor_type == "current":
            return SensorDeviceClass.CURRENT
        elif self._sensor_type == "voltage":
            return SensorDeviceClass.VOLTAGE
        return None

    @property
    def suggested_display_precision(self) -> Optional[int]:
        """Return the suggested display precision for this sensor."""
        if self._sensor_type == "current":
            return 2  # 2 decimal places for current
        elif self._sensor_type in ["power", "voltage"]:
            return 0  # 0 decimal places for power and voltage
        return None

    async def async_update(self) -> None:
        """Update the sensor."""
        # Call parent update first
        await super().async_update()
        
        # For power-related sensors, try to get fresh power data periodically
        if self._sensor_type in ["power", "current", "voltage"]:
            current_time = time.time()
            # Update power data every 30 seconds to avoid excessive API calls
            if current_time - self._last_power_update > 30:
                try:
                    # Try to get individual outlet power data
                    self._cached_power_data = await self.coordinator.get_outlet_power_info(self._outlet_index)
                    self._last_power_update = current_time
                    _LOGGER.debug(f"Updated power info for outlet {self._outlet_index}: {self._cached_power_data}")
                except Exception as err:
                    _LOGGER.debug(f"Could not update power info for outlet {self._outlet_index}: {err}")
                    # Clear cached data if we can't get it
                    self._cached_power_data = None

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if not self.coordinator.data or not self.coordinator.data.get("outlets"):
            return None
        
        # For power-related sensors, first try cached power data from individual outlet queries
        if self._sensor_type in ["power", "current", "voltage"] and self._cached_power_data:
            if self._sensor_type == "power":
                value = self._cached_power_data.get("power_watts")
                if value is not None:
                    return value
            elif self._sensor_type == "current":
                value = self._cached_power_data.get("current_amps")
                if value is not None:
                    return value
            elif self._sensor_type == "voltage":
                value = self._cached_power_data.get("voltage_volts")
                if value is not None:
                    return value
        
        # Fall back to coordinator data for basic outlet info (though this will likely be None for power data)
        for outlet in self.coordinator.data["outlets"]:
            if outlet.index == self._outlet_index:
                if self._sensor_type == "power":
                    return outlet.power_watts
                elif self._sensor_type == "current":
                    return outlet.current_amps
                elif self._sensor_type == "voltage":
                    return outlet.voltage_volts
        
        # If no data is available, return None (sensor will show as unavailable)
        return None
