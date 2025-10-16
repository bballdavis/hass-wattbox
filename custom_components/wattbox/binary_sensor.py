"""Binary sensor platform for wattbox."""

import logging
from typing import Optional

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import DOMAIN, get_outlet_device_info, get_wattbox_device_info, canonicalize_name, friendly_name, get_outlet_device_info_canonical, get_wattbox_device_info_canonical, unique_wattbox_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WattBox binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    main_device_name = entry.data.get("name") or entry.title or "wattbox"
    canonical_main_device = canonicalize_name(main_device_name)
    entry_id = entry.entry_id
    # System binary sensors (on main WattBox device)
    entities.append(WattBoxAutoRebootSensor(coordinator, canonical_main_device, friendly_name(main_device_name, sensor_type="Auto Reboot Enabled"), entry_id=entry_id))
    entities.append(WattBoxUPSConnectedSensor(coordinator, canonical_main_device, friendly_name(main_device_name, sensor_type="UPS Connected"), entry_id=entry_id))
    
    # UPS on battery status (if UPS is connected, on main WattBox device)
    if coordinator.data and coordinator.data.get("ups_connected"):
        entities.append(WattBoxUPSOnBatterySensor(coordinator, canonical_main_device, friendly_name(main_device_name, sensor_type="UPS On Battery"), entry_id=entry_id))
    
    # Individual outlet status sensors (on individual outlet devices)
    if coordinator.data and coordinator.data.get("outlets"):
        for outlet in coordinator.data["outlets"]:
            sensor_name = friendly_name(main_device_name, outlet.index, "Status")
            entities.append(WattBoxOutletStatusSensor(coordinator, canonical_main_device, outlet.index, outlet.name, sensor_name, entry_id=entry_id))
    async_add_entities(entities)


class WattBoxBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base class for WattBox binary sensors."""

    def __init__(self, coordinator, main_device: str, sensor_type: str, name: str, device_class: Optional[BinarySensorDeviceClass] = None, entry_id: Optional[str] = None):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._sensor_type = sensor_type
        self._attr_name = name
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, sensor_type)
        if device_class:
            self._attr_device_class = device_class

    @property
    def device_info(self):
        """Return device information for main WattBox device."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        return get_wattbox_device_info_canonical(self._main_device, system_info)


class WattBoxAutoRebootSensor(WattBoxBaseBinarySensor):
    """Auto reboot status sensor."""

    def __init__(self, coordinator, main_device: str, name: str, entry_id: Optional[str] = None):
        super().__init__(coordinator, main_device, "auto_reboot", name, entry_id=entry_id)

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if auto reboot is enabled."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("auto_reboot_enabled", False)


class WattBoxUPSConnectedSensor(WattBoxBaseBinarySensor):
    """UPS connected status sensor."""

    def __init__(self, coordinator, main_device: str, name: str, entry_id: Optional[str] = None):
        super().__init__(coordinator, main_device, "ups_connected", name, BinarySensorDeviceClass.CONNECTIVITY, entry_id=entry_id)

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if UPS is connected."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("ups_connected", False)


class WattBoxUPSOnBatterySensor(WattBoxBaseBinarySensor):
    """UPS on battery status sensor."""

    def __init__(self, coordinator, main_device: str, name: str, entry_id: Optional[str] = None):
        super().__init__(coordinator, main_device, "ups_on_battery", name, BinarySensorDeviceClass.BATTERY, entry_id=entry_id)

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if UPS is on battery."""
        if not self.coordinator.data or not self.coordinator.data.get("ups_status"):
            return None
        ups_status = self.coordinator.data["ups_status"]
        return getattr(ups_status, "on_battery", False)


class WattBoxOutletStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Outlet status binary sensor."""

    def __init__(self, coordinator, main_device: str, outlet_index: int, outlet_name: str, name: str, entry_id: Optional[str] = None):
        """Initialize the outlet status sensor."""
        super().__init__(coordinator)
        self._main_device = main_device
        self._outlet_index = outlet_index
        self._outlet_name = outlet_name
        self._entry_id = entry_id
        self._attr_unique_id = unique_wattbox_entity_id(entry_id, main_device, f"outlet_{outlet_index}", "status")
        # Compose friendly name as "<Main Device> <Outlet Name> Status"
        self._attr_name = f"{main_device.replace('_', ' ').title()} {outlet_name} Status"
        self._attr_device_class = BinarySensorDeviceClass.POWER

    @property
    def device_info(self):
        """Return device information for this outlet device, using the main device and outlet name as the device name."""
        system_info = self.coordinator.data.get("system_info") if self.coordinator.data else None
        # Compose device name as "<Main Device> <Outlet Name>"
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
