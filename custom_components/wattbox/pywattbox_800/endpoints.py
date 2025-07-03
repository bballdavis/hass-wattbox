"""
WattBox API Endpoints

Constants and utilities for WattBox API endpoints.
"""

from typing import Dict, Any, Optional


class WattBoxEndpoints:
    """WattBox API endpoint constants and formatters."""
    
    # Query endpoints (request information)
    FIRMWARE = "?Firmware"
    HOSTNAME = "?Hostname"
    SERVICE_TAG = "?ServiceTag"
    MODEL = "?Model"
    OUTLET_COUNT = "?OutletCount"
    OUTLET_STATUS = "?OutletStatus"
    OUTLET_NAMES = "?OutletName"
    POWER_STATUS = "?PowerStatus"
    AUTO_REBOOT = "?AutoReboot"
    UPS_STATUS = "?UPSStatus"
    UPS_CONNECTION = "?UPSConnection"
    
    # Control endpoints (send commands)
    OUTLET_SET = "!OutletSet"
    OUTLET_NAME_SET = "!OutletNameSet"
    OUTLET_NAME_SET_ALL = "!OutletNameSetAll"
    OUTLET_POWER_ON_DELAY_SET = "!OutletPowerOnDelaySet"
    OUTLET_MODE_SET = "!OutletModeSet"
    OUTLET_REBOOT_SET = "!OutletRebootSet"
    AUTO_REBOOT_SET = "!AutoReboot"
    AUTO_REBOOT_TIMEOUT_SET = "!AutoRebootTimeoutSet"
    ACCOUNT_SET = "!AccountSet"
    NETWORK_SET = "!NetworkSet"
    SCHEDULE_ADD = "!ScheduleAdd"
    HOST_ADD = "!HostAdd"
    SET_TELNET = "!SetTelnet"
    WEB_SERVER_SET = "!WebServerSet"
    SET_SDDP = "!SetSDDP"
    FIRMWARE_UPDATE = "!FirmwareUpdate"
    REBOOT = "!Reboot"
    EXIT = "!Exit"
    
    @staticmethod
    def outlet_power_status(outlet: int) -> str:
        """Get outlet power status command for specific outlet."""
        return f"?OutletPowerStatus={outlet}"
    
    @staticmethod
    def outlet_set(outlet: int, action: str, delay: Optional[int] = None) -> str:
        """Set outlet state command."""
        if delay is not None:
            return f"!OutletSet={outlet},{action},{delay}"
        return f"!OutletSet={outlet},{action}"
    
    @staticmethod
    def outlet_name_set(outlet: int, name: str) -> str:
        """Set single outlet name command."""
        return f"!OutletNameSet={outlet},{name}"
    
    @staticmethod
    def outlet_name_set_all(names: list) -> str:
        """Set all outlet names command."""
        formatted_names = ",".join([f"{{{name}}}" for name in names])
        return f"!OutletNameSetAll={formatted_names}"
    
    @staticmethod
    def outlet_power_on_delay_set(outlet: int, delay: int) -> str:
        """Set outlet power on delay command."""
        return f"!OutletPowerOnDelaySet={outlet},{delay}"
    
    @staticmethod
    def outlet_mode_set(outlet: int, mode: int) -> str:
        """Set outlet mode command."""
        return f"!OutletModeSet={outlet},{mode}"
    
    @staticmethod
    def outlet_reboot_set(operations: list) -> str:
        """Set outlet reboot operations command."""
        ops_str = ",".join(str(op) for op in operations)
        return f"!OutletRebootSet={ops_str}"
    
    @staticmethod
    def auto_reboot_set(enabled: bool) -> str:
        """Set auto reboot state command."""
        state = 1 if enabled else 0
        return f"!AutoReboot={state}"
    
    @staticmethod
    def auto_reboot_timeout_set(timeout: int, count: int, ping_delay: int, reboot_attempts: int) -> str:
        """Set auto reboot timeout settings command."""
        return f"!AutoRebootTimeoutSet={timeout},{count},{ping_delay},{reboot_attempts}"
    
    @staticmethod
    def account_set(username: str, password: str) -> str:
        """Set account credentials command."""
        return f"!AccountSet={username},{password}"
    
    @staticmethod
    def network_set(hostname: str, ip: Optional[str] = None, subnet: Optional[str] = None, 
                   gateway: Optional[str] = None, dns1: Optional[str] = None, dns2: Optional[str] = None) -> str:
        """Set network configuration command."""
        if ip is None:
            # DHCP mode
            return f"!NetworkSet={hostname}"
        else:
            # Static mode
            dns2 = dns2 or "8.8.8.8"
            return f"!NetworkSet={hostname},{ip},{subnet},{gateway},{dns1},{dns2}"
    
    @staticmethod
    def schedule_add(name: str, outlets: list, action: int, frequency: int, 
                    days_or_date: str, time: str) -> str:
        """Add schedule command."""
        outlets_str = ",".join(str(outlet) for outlet in outlets)
        return f"!ScheduleAdd={{{name}}},{{{outlets_str}}},{{{action}}},{{{frequency}}},{{{days_or_date}}},{{{time}}}"
    
    @staticmethod
    def host_add(name: str, ip: str, outlets: list) -> str:
        """Add host monitoring command."""
        outlets_str = ",".join(str(outlet) for outlet in outlets)
        return f"!HostAdd={name},{ip},{{{outlets_str}}}"
    
    @staticmethod
    def set_telnet(enabled: bool) -> str:
        """Set telnet service state command."""
        mode = 1 if enabled else 0
        return f"!SetTelnet={mode}"
    
    @staticmethod
    def web_server_set(enabled: bool) -> str:
        """Set web server state command."""
        mode = 1 if enabled else 0
        return f"!WebServerSet={mode}"
    
    @staticmethod
    def set_sddp(enabled: bool) -> str:
        """Set SDDP broadcasting state command."""
        mode = 1 if enabled else 0
        return f"!SetSDDP={mode}"
    
    @staticmethod
    def firmware_update(url: str) -> str:
        """Firmware update command."""
        return f"!FirmwareUpdate={url}"


# Command validation
VALID_OUTLET_ACTIONS = {"ON", "OFF", "TOGGLE", "RESET"}
VALID_OUTLET_MODES = {0, 1, 2}  # Enabled, Disabled, Reset Only
VALID_REBOOT_OPERATIONS = {0, 1}  # OR, AND
VALID_SCHEDULE_ACTIONS = {0, 1, 2}  # Off, On, Reset
VALID_SCHEDULE_FREQUENCIES = {0, 1}  # Once, Recurring

# Response prefixes
RESPONSE_PREFIXES = {
    "QUERY": "?",
    "CONTROL": "!",
    "ERROR": "#",
    "UNSOLICITED": "~"
}

# Common response patterns
SUCCESS_RESPONSE = "OK"
ERROR_RESPONSE = "#Error"
COMMAND_TERMINATOR = "\n"
