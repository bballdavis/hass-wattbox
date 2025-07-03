"""
WattBox API Data Models

Data classes representing WattBox device information and responses.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class OutletAction(Enum):
    """Outlet control actions."""
    ON = "ON"
    OFF = "OFF"
    TOGGLE = "TOGGLE"
    RESET = "RESET"


class OutletMode(Enum):
    """Outlet operating modes."""
    ENABLED = 0
    DISABLED = 1
    RESET_ONLY = 2


class RebootOperation(Enum):
    """Reboot operations for host monitoring."""
    OR = 0  # Any selected hosts timeout
    AND = 1  # All selected hosts timeout


@dataclass
class OutletInfo:
    """Information about a specific outlet."""
    index: int
    name: str
    status: bool  # True = on, False = off
    power_watts: Optional[float] = None
    current_amps: Optional[float] = None
    voltage_volts: Optional[float] = None
    mode: Optional[OutletMode] = None
    power_on_delay: Optional[int] = None


@dataclass
class PowerStatus:
    """System-wide power status."""
    current_amps: float
    power_watts: float
    voltage_volts: float
    safe_voltage_status: bool


@dataclass
class UPSStatus:
    """UPS status information."""
    battery_charge: int  # Changed from battery_charge_percent
    battery_load: int    # Changed from battery_load_percent
    battery_health: str  # "Good" or "Bad"
    power_lost: bool
    battery_runtime: int  # Changed from battery_runtime_minutes
    alarm_enabled: bool
    alarm_muted: bool


@dataclass
class SystemInfo:
    """Device system information."""
    firmware: str
    hostname: str
    service_tag: str
    model: str
    outlet_count: int


@dataclass
class WattBoxDevice:
    """Complete WattBox device state."""
    system_info: SystemInfo
    outlets: List[OutletInfo]
    power_status: Optional[PowerStatus] = None
    ups_status: Optional[UPSStatus] = None
    ups_connected: bool = False
    auto_reboot_enabled: bool = False


@dataclass
class ScheduleInfo:
    """Schedule configuration."""
    name: str
    outlets: List[int]
    action: OutletAction
    frequency: str  # "once" or "recurring"
    days_or_date: str
    time: str


@dataclass
class HostInfo:
    """Host monitoring configuration."""
    name: str
    ip_address: str
    outlets: List[int]


# Response parsing helpers
def parse_outlet_status_response(response: str) -> List[bool]:
    """Parse ?OutletStatus response into list of boolean states."""
    # Response format: ?OutletStatus=0,0,0,0,0,0,0,0,0,0,0,0\n
    if not response.startswith("?OutletStatus="):
        raise ValueError(f"Invalid outlet status response: {response}")
    
    status_part = response.replace("?OutletStatus=", "").strip()
    status_values = status_part.split(",")
    return [bool(int(val)) for val in status_values if val.isdigit()]


def parse_outlet_names_response(response: str) -> List[str]:
    """Parse ?OutletName response into list of outlet names."""
    # Response format: ?OutletName={Outlet 1},{Outlet 2},{Outlet 3}...\n
    if not response.startswith("?OutletName="):
        raise ValueError(f"Invalid outlet names response: {response}")
    
    names_part = response.replace("?OutletName=", "").strip()
    names = []
    
    # Parse names enclosed in braces
    import re
    matches = re.findall(r'\{([^}]*)\}', names_part)
    return matches


def parse_outlet_power_response(response: str) -> OutletInfo:
    """Parse ?OutletPowerStatus response."""
    # Response format: ?OutletPowerStatus=1,1.01,0.02,116.50\n
    if not response.startswith("?OutletPowerStatus="):
        raise ValueError(f"Invalid outlet power response: {response}")
    
    power_part = response.replace("?OutletPowerStatus=", "").strip()
    values = power_part.split(",")
    
    if len(values) != 4:
        raise ValueError(f"Expected 4 values in power response, got {len(values)}: {response}")
    
    try:
        return OutletInfo(
            index=int(values[0]),
            name=f"Outlet {values[0]}",  # Default name, will be updated elsewhere
            status=True,  # We don't know status from this response
            power_watts=float(values[1]),
            current_amps=float(values[2]),
            voltage_volts=float(values[3])
        )
    except (ValueError, IndexError) as err:
        raise ValueError(f"Failed to parse outlet power values {values}: {err}")


def parse_power_status_response(response: str) -> PowerStatus:
    """Parse ?PowerStatus response."""
    # Response format: ?PowerStatus=60.00,600.00,110.00,1\n
    # But some devices might return just the values: 60.00,600.00,110.00,1
    
    response = response.strip()
    
    # Handle both formats - with and without the command prefix
    if response.startswith("?PowerStatus="):
        power_part = response.replace("?PowerStatus=", "")
    elif "," in response and not response.startswith("?"):
        # Looks like raw power data without prefix
        power_part = response
    else:
        # Check if we got a different response (device confusion)
        if response.startswith("?OutletName="):
            raise ValueError(f"Device returned outlet names instead of power status. Device may not support PowerStatus command: {response}")
        raise ValueError(f"Invalid power status response format: {response}")
    
    power_part = power_part.strip()
    values = power_part.split(",")
    
    if len(values) != 4:
        raise ValueError(f"Expected 4 values in power status response, got {len(values)}: {response}")
    
    try:
        return PowerStatus(
            current_amps=float(values[0]),
            power_watts=float(values[1]),
            voltage_volts=float(values[2]),
            safe_voltage_status=bool(int(values[3]))
        )
    except (ValueError, IndexError) as err:
        raise ValueError(f"Failed to parse power status values {values}: {err}")


def parse_ups_status_response(response: str) -> UPSStatus:
    """Parse ?UPSStatus response."""
    # Response format: ?UPSStatus=50,0,Good,False,25,True,False\n
    if not response.startswith("?UPSStatus="):
        raise ValueError(f"Invalid UPS status response: {response}")
    
    ups_part = response.replace("?UPSStatus=", "").strip()
    values = ups_part.split(",")
    
    if len(values) != 7:
        raise ValueError(f"Expected 7 values in UPS status response, got {len(values)}")
    
    return UPSStatus(
        battery_charge=int(values[0]),
        battery_load=int(values[1]),
        battery_health=values[2],
        power_lost=values[3].lower() == "true",
        battery_runtime=int(values[4]),
        alarm_enabled=values[5].lower() == "true",
        alarm_muted=values[6].lower() == "true"
    )
