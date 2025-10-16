"""
WattBox API Utilities

Helper functions and utilities for WattBox API operations.
"""

import re
import socket
import time
from typing import List, Optional, Tuple, Any
from .exceptions import WattBoxResponseError, WattBoxTimeoutError


def validate_ip_address(ip: str) -> bool:
    """Validate if a string is a valid IP address."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def validate_port(port: int) -> bool:
    """Validate if a port number is valid."""
    return 1 <= port <= 65535


def validate_outlet_number(outlet: int, max_outlets: int) -> bool:
    """Validate if an outlet number is valid."""
    return 1 <= outlet <= max_outlets


def validate_delay(delay: int) -> bool:
    """Validate if a delay value is within acceptable range (1-600 seconds)."""
    return 1 <= delay <= 600


def validate_timeout_settings(timeout: int, count: int, ping_delay: int, reboot_attempts: int) -> bool:
    """Validate auto reboot timeout settings."""
    timeout_valid = 1 <= timeout <= 60
    count_valid = 1 <= count <= 10
    ping_delay_valid = 1 <= ping_delay <= 30
    reboot_attempts_valid = 0 <= reboot_attempts <= 10
    
    return all([timeout_valid, count_valid, ping_delay_valid, reboot_attempts_valid])


def parse_response_line(line: str) -> Tuple[str, str]:
    """Parse a response line into prefix and content."""
    if not line:
        raise WattBoxResponseError("Empty response line")
    
    prefix = line[0]
    content = line[1:].strip()
    
    return prefix, content


def is_success_response(response: str) -> bool:
    """Check if response indicates success."""
    return response.strip() == "OK"


def is_error_response(response: str) -> bool:
    """Check if response indicates an error."""
    return response.strip().startswith("#Error")


def format_command(command: str) -> str:
    """Format a command with proper termination."""
    if not command.endswith("\n"):
        command += "\n"
    return command


def parse_comma_separated_values(data: str) -> List[str]:
    """Parse comma-separated values from response data."""
    return [item.strip() for item in data.split(",") if item.strip()]


def parse_bracketed_values(data: str) -> List[str]:
    """Parse values enclosed in brackets from response data."""
    pattern = r'\{([^}]*)\}'
    matches = re.findall(pattern, data)
    return matches


def retry_on_failure(func, max_retries: int = 3, delay: float = 1.0):
    """Retry a function on failure with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay * (2 ** attempt))


def sanitize_outlet_name(name: str, max_length: int = 32) -> str:
    """Sanitize outlet name for API usage."""
    # Remove characters that might interfere with protocol
    sanitized = re.sub(r'[{},\n\r]', '', name)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def format_schedule_days(days: List[bool]) -> str:
    """Format days array for schedule commands."""
    if len(days) != 7:
        raise ValueError("Days array must have exactly 7 elements")
    
    return ",".join("1" if day else "0" for day in days)


def format_schedule_time(hour: int, minute: int) -> str:
    """Format time for schedule commands (24-hour format)."""
    if not (0 <= hour <= 23):
        raise ValueError("Hour must be between 0 and 23")
    if not (0 <= minute <= 59):
        raise ValueError("Minute must be between 0 and 59")
    
    return f"{hour:02d}:{minute:02d}"


def format_schedule_date(year: int, month: int, day: int) -> str:
    """Format date for schedule commands."""
    if not (1900 <= year <= 2100):
        raise ValueError("Year must be between 1900 and 2100")
    if not (1 <= month <= 12):
        raise ValueError("Month must be between 1 and 12")
    if not (1 <= day <= 31):
        raise ValueError("Day must be between 1 and 31")
    
    return f"{year:04d}/{month:02d}/{day:02d}"


class ResponseBuffer:
    """Buffer for collecting multi-line responses."""
    
    def __init__(self):
        self.lines: List[str] = []
        self.complete = False
    
    def add_line(self, line: str) -> None:
        """Add a line to the buffer."""
        self.lines.append(line.strip())
    
    def is_complete(self) -> bool:
        """Check if the response is complete."""
        if not self.lines:
            return False
        
        last_line = self.lines[-1]
        # Response is complete if last line is an OK, Error, or query response
        return (last_line == "OK" or 
                last_line.startswith("#Error") or
                last_line.startswith("?"))
    
    def get_response(self) -> str:
        """Get the complete response."""
        return "\n".join(self.lines)
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.lines.clear()
        self.complete = False


def calculate_timeout(command_type: str, default_timeout: float = 10.0) -> float:
    """Calculate appropriate timeout based on command type."""
    # Some commands take longer than others
    timeout_map = {
        "reboot": 60.0,
        "firmware_update": 300.0,
        "network_set": 30.0,
        "account_set": 15.0,
        "default": default_timeout
    }
    
    return timeout_map.get(command_type, timeout_map["default"])


def discover_wattbox_devices(subnet: str = "192.168.1", port: int = 23, timeout: float = 2.0) -> List[str]:
    """
    Discover WattBox devices on the network by attempting connections.
    
    Args:
        subnet: Network subnet to scan (e.g., "192.168.1")
        port: Port to scan (default 23 for Telnet)
        timeout: Connection timeout in seconds
    
    Returns:
        List of IP addresses where WattBox devices were found
    """
    devices = []
    
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        try:
            result = sock.connect_ex((ip, port))
            if result == 0:
                # Connection successful, might be a WattBox
                devices.append(ip)
        except Exception:
            pass
        finally:
            sock.close()
    
    return devices
