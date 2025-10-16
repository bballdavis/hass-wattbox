"""Constants for wattbox."""

from datetime import timedelta
from typing import Dict, Final, List, TypedDict

from homeassistant.components.binary_sensor import BinarySensorDeviceClass # type: ignore
from homeassistant.const import ( # type: ignore
    UnitOfElectricPotential,
    PERCENTAGE,
    UnitOfPower,
    UnitOfTime,
)

# Base component constants
DOMAIN: Final[str] = "wattbox"
DOMAIN_DATA: Final[str] = f"{DOMAIN}_data"
VERSION: Final[str] = "0.8.2"
PLATFORMS: Final[List[str]] = ["binary_sensor", "sensor", "switch"]
REQUIRED_FILES: Final[List[str]] = [
    "binary_sensor.py",
    "const.py",
    "sensor.py",
    "switch.py",
]
ISSUE_URL: Final[str] = "https://github.com/bballdavis/hass-wattbox/issues"

STARTUP: Final[
    str
] = f"""
-------------------------------------------------------------------
{DOMAIN}
Version: {VERSION}
This is a custom component
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Icons
ICON: Final[str] = "mdi:power"
PLUG_ICON: Final[str] = "mdi:power-socket-us"

# Defaults
DEFAULT_NAME: Final[str] = "WattBox"
DEFAULT_PASSWORD: Final[str] = "wattbox"
DEFAULT_PORT: Final[int] = 23
DEFAULT_USER: Final[str] = "wattbox"
DEFAULT_SCAN_INTERVAL: Final[timedelta] = timedelta(seconds=30)

# Configuration options
CONF_ENABLE_POWER_SENSORS: Final[str] = "enable_power_sensors"
DEFAULT_ENABLE_POWER_SENSORS: Final[bool] = True

TOPIC_UPDATE: Final[str] = "{}_data_update_{}"


class _BinarySensorDict(TypedDict):
    """TypedDict for use in BINARY_SENSOR_TYPES"""

    name: str
    device_class: BinarySensorDeviceClass | None
    flipped: bool


BINARY_SENSOR_TYPES: Final[Dict[str, _BinarySensorDict]] = {
    "audible_alarm": {
        "name": "Audible Alarm",
        "device_class": BinarySensorDeviceClass.SOUND,
        "flipped": False,
    },
    "auto_reboot": {"name": "Auto Reboot", "device_class": None, "flipped": False},
    "battery_health": {
        "name": "Battery Health",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "flipped": True,
    },
    "battery_test": {"name": "Battery Test", "device_class": None, "flipped": False},
    "cloud_status": {
        "name": "Cloud Status",
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "flipped": False,
    },
    "has_ups": {"name": "Has UPS", "device_class": None, "flipped": False},
    "mute": {"name": "Mute", "device_class": None, "flipped": False},
    "power_lost": {
        "name": "Power",
        "device_class": BinarySensorDeviceClass.PLUG,
        "flipped": True,
    },
    "safe_voltage_status": {
        "name": "Safe Voltage Status",
        "device_class": BinarySensorDeviceClass.SAFETY,
        "flipped": True,
    },
}


class _SensorTypeDict(TypedDict):
    name: str
    unit: str
    icon: str


SENSOR_TYPES: Final[Dict[str, _SensorTypeDict]] = {
    "battery_charge": {
        "name": "Battery Charge",
        "unit": PERCENTAGE,
        "icon": "mdi:battery",
    },
    "battery_load": {"name": "Battery Load", "unit": PERCENTAGE, "icon": "mdi:gauge"},
    "current_value": {"name": "Current", "unit": "A", "icon": "mdi:current-ac"},
    "est_run_time": {
        "name": "Estimated Run Time",
        "unit": UnitOfTime.MINUTES,
        "icon": "mdi:timer",
    },
    "power_value": {
        "name": "Power",
        "unit": UnitOfPower.WATT,
        "icon": "mdi:lightbulb-outline",
    },
    "voltage_value": {
        "name": "Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "icon": "mdi:lightning-bolt-circle",
    },
}

# Outlet-specific sensor types
OUTLET_SENSOR_TYPES: Final[Dict[str, _SensorTypeDict]] = {
    "power": {
        "name": "Power",
        "unit": UnitOfPower.WATT,
        "icon": "mdi:lightbulb-outline",
    },
    "current": {
        "name": "Current",
        "unit": "A", 
        "icon": "mdi:current-ac",
    },
    "voltage": {
        "name": "Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "icon": "mdi:lightning-bolt-circle",
    },
}

def canonicalize_name(name: str) -> str:
    """Convert a name to a canonical entity/device id (lowercase, underscores, no spaces)."""
    return name.replace(" ", "_").replace("-", "_").lower()

def friendly_name(main_device: str, outlet_index: int = None, sensor_type: str = None) -> str:
    """Generate a friendly name for an entity."""
    base = main_device.replace("_", " ").title()
    if outlet_index is not None and sensor_type is not None:
        return f"{base} Outlet {outlet_index} {sensor_type.title()}"
    elif outlet_index is not None:
        return f"{base} Outlet {outlet_index}"
    elif sensor_type is not None:
        return f"{base} {sensor_type.title()}"
    return base

def get_outlet_device_info_canonical(main_device: str, outlet_index: int, wattbox_system_info=None, device_name: str = None):
    """Get device info for an outlet device with canonical name, allowing override of device name."""
    canonical = canonicalize_name(main_device)
    return {
        "identifiers": {(DOMAIN, f"{canonical}_outlet_{outlet_index}")},
        "name": device_name if device_name is not None else friendly_name(main_device, outlet_index),
        "manufacturer": "SnapAV",
        "model": f"WattBox Outlet {outlet_index}",
        "via_device": (DOMAIN, canonical),
        "sw_version": getattr(wattbox_system_info, "firmware", "Unknown") if wattbox_system_info else "Unknown",
    }

def get_wattbox_device_info_canonical(main_device: str, system_info=None):
    """Get device info for the main WattBox device with canonical name."""
    canonical = canonicalize_name(main_device)
    return {
        "identifiers": {(DOMAIN, canonical)},
        "name": friendly_name(main_device),
        "manufacturer": "SnapAV",
        "model": getattr(system_info, "model", "Unknown") if system_info else "Unknown",
        "sw_version": getattr(system_info, "firmware", "Unknown") if system_info else "Unknown",
    }

def get_outlet_device_info(host: str, outlet_index: int, outlet_name: str, wattbox_system_info=None):
    """Get device info for an outlet device."""
    return {
        "identifiers": {(DOMAIN, f"{host}_outlet_{outlet_index}")},
        "name": outlet_name,
        "manufacturer": "SnapAV",
        "model": f"WattBox Outlet {outlet_index}",
        "via_device": (DOMAIN, host),
        "sw_version": getattr(wattbox_system_info, "firmware", "Unknown") if wattbox_system_info else "Unknown",
    }

def get_wattbox_device_info(host: str, system_info=None):
    """Get device info for the main WattBox device."""
    return {
        "identifiers": {(DOMAIN, host)},
        "name": "WattBox",
        "manufacturer": "SnapAV",
        "model": getattr(system_info, "model", "Unknown") if system_info else "Unknown",
        "sw_version": getattr(system_info, "firmware", "Unknown") if system_info else "Unknown",
    }

def extract_outlet_number_from_model(model: str) -> int:
    """Extract outlet number from WattBox outlet device model string.
    
    Args:
        model: Model string in format "WattBox Outlet <number>"
        
    Returns:
        int: The outlet number, or 0 if not found
    """
    try:
        if model and model.startswith("WattBox Outlet "):
            # Extract the number from "WattBox Outlet <number>"
            outlet_num_str = model.replace("WattBox Outlet ", "").strip()
            return int(outlet_num_str)
    except (ValueError, AttributeError):
        pass
    return 0

def extract_outlet_number_from_device_model(device_model: str) -> int:
    """Extract outlet number from our device model string.
    
    Our device models are formatted as: "WattBox Outlet <number>"
    This function extracts the outlet number for use in API commands.
    """
    import re
    
    # Look for "WattBox Outlet <number>" pattern
    match = re.search(r'WattBox Outlet (\d+)', device_model)
    if match:
        return int(match.group(1))
    
    # Fallback - look for any number in the string
    numbers = re.findall(r'\d+', device_model)
    if numbers:
        return int(numbers[-1])  # Take the last number found
    
    raise ValueError(f"Could not extract outlet number from device model: {device_model}")

def extract_outlet_count_from_model_name(model_name: str) -> int:
    """Extract outlet count from WattBox model name.
    
    Many WattBox models include the outlet count in their model name.
    For example: WB-800-IPVM-12 indicates 12 outlets.
    
    Args:
        model_name: The model name string
        
    Returns:
        int: The number of outlets, or 8 as default if not found
    """
    if not model_name:
        return 8  # Default fallback
        
    # Look for common patterns in WattBox model names
    # Pattern: WB-XXX-XXX-XX where the last number is outlet count
    parts = model_name.split('-')
    if len(parts) >= 4 and parts[0] == "WB":
        try:
            return int(parts[-1])
        except ValueError:
            pass
    
    # Look for other patterns with numbers at the end
    import re
    match = re.search(r'-(\d+)$', model_name)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    
    # Default fallback for unknown models
    return 8

# Utility to build a unique entity id for a given integration instance

def unique_wattbox_entity_id(entry_id: str, *parts: str) -> str:
    """Generate a unique entity id for a WattBox entity using the config entry id and other parts."""
    return "_".join([entry_id] + [canonicalize_name(p) for p in parts if p])
