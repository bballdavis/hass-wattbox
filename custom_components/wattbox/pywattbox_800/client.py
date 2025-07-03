"""
WattBox API Client

Main client class for communicating with SnapAV WattBox devices.
"""

import socket
import time
import logging
import threading
from typing import Optional, List, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from .exceptions import (
    WattBoxError,
    WattBoxConnectionError,
    WattBoxAuthenticationError,
    WattBoxCommandError,
    WattBoxTimeoutError,
    WattBoxResponseError,
)
from .models import (
    WattBoxDevice,
    OutletInfo,
    PowerStatus,
    UPSStatus,
    SystemInfo,
    OutletAction,
    OutletMode,
    parse_outlet_status_response,
    parse_outlet_names_response,
    parse_outlet_power_response,
    parse_power_status_response,
    parse_ups_status_response,
)
from .endpoints import WattBoxEndpoints
from .utils import (
    validate_ip_address,
    validate_port,
    validate_outlet_number,
    format_command,
    is_success_response,
    is_error_response,
    parse_response_line,
    calculate_timeout,
)

logger = logging.getLogger(__name__)


class WattBoxClient:
    """
    Client for communicating with SnapAV WattBox devices via Telnet or SSH.
    
    Supports the Integration Protocol v2.4 for controlling and monitoring
    WattBox power distribution units.
    """
    
    def __init__(
        self,
        host: str,
        port: int = 23,
        username: str = "wattbox",
        password: str = "wattbox",
        timeout: float = 10.0,
        connection_type: str = "telnet"
    ):
        """
        Initialize WattBox client.
        
        Args:
            host: IP address of WattBox device
            port: Port number (23 for Telnet, 22 for SSH)
            username: Authentication username
            password: Authentication password
            timeout: Default command timeout in seconds
            connection_type: "telnet" or "ssh"
        """
        if not validate_ip_address(host):
            raise ValueError(f"Invalid IP address: {host}")
        
        if not validate_port(port):
            raise ValueError(f"Invalid port: {port}")
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.connection_type = connection_type.lower()
        
        self._connection: Optional[socket.socket] = None
        self._authenticated = False
        self._device_info: Optional[WattBoxDevice] = None
        
        # Thread lock to prevent simultaneous commands
        self._command_lock = threading.RLock()
        
        # Cache for device capabilities
        self._outlet_count: Optional[int] = None
        self._model: Optional[str] = None
        self._firmware: Optional[str] = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def connect(self) -> None:
        """Establish connection to WattBox device."""
        try:
            logger.debug(f"Connecting to WattBox at {self.host}:{self.port}")
            
            if self.connection_type == "telnet":
                # Create socket connection
                self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._connection.settimeout(self.timeout)
                self._connection.connect((self.host, self.port))
            else:
                raise NotImplementedError("SSH connections not yet implemented")
            
            # Authenticate
            self._authenticate()
            
            logger.info(f"Successfully connected to WattBox at {self.host}")
            
        except socket.error as e:
            self._cleanup_connection()
            raise WattBoxConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")
        except Exception as e:
            self._cleanup_connection()
            raise WattBoxConnectionError(f"Unexpected connection error: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from WattBox device."""
        if self._connection:
            try:
                # Send exit command gracefully
                if self._authenticated:
                    self._send_command(WattBoxEndpoints.EXIT)
            except Exception:
                pass  # Ignore errors during graceful exit
            
            try:
                self._connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            
            self._connection = None
            self._authenticated = False
            self._connected = False
            
            logger.debug(f"Disconnected from WattBox at {self.host}")
    
    def _authenticate(self) -> None:
        """Authenticate with the WattBox device."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        
        try:
            # Wait for login prompt - try multiple variations
            response = self._wait_for_login_prompt()
            logger.debug(f"Login prompt received: {response.decode('utf-8', errors='ignore')}")
            
            # Send username
            self._send_raw(self.username + "\r\n")
            
            # Wait for password prompt
            response = self._wait_for_password_prompt()
            logger.debug(f"Password prompt received: {response.decode('utf-8', errors='ignore')}")
            
            # Send password
            self._send_raw(self.password + "\r\n")
            
            # Check for successful login by waiting for a command prompt or reading response
            time.sleep(1)  # Give device time to process login
            response = self._read_available_data()
            
            # Check if we got rejected (login prompt again)
            if any(prompt in response.lower() for prompt in ["login:", "username:", "invalid", "incorrect"]):
                raise WattBoxAuthenticationError("Invalid credentials")
            
            self._authenticated = True
            logger.debug("Authentication successful")
            
        except socket.timeout:
            raise WattBoxTimeoutError("Authentication timeout")
        except (WattBoxTimeoutError, WattBoxAuthenticationError):
            raise
        except Exception as e:
            raise WattBoxAuthenticationError(f"Authentication failed: {e}")
    
    def _cleanup_connection(self) -> None:
        """Clean up connection resources."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass  # Ignore errors during cleanup
            self._connection = None
            self._authenticated = False

    def _wait_for_login_prompt(self) -> bytes:
        """Wait for login prompt from WattBox device."""
        login_prompts = [b"login:", b"username:", b"user:"]
        return self._wait_for_prompts(login_prompts)

    def _wait_for_password_prompt(self) -> bytes:
        """Wait for password prompt from WattBox device."""
        password_prompts = [b"password:", b"pass:"]
        return self._wait_for_prompts(password_prompts)

    def _wait_for_prompts(self, prompts: list, timeout: Optional[float] = None) -> bytes:
        """Wait for any of the specified prompts."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        if timeout is None:
            timeout = self.timeout
        buffer = b""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self._connection.settimeout(0.1)
                data = self._connection.recv(1024)
                if not data:
                    break
                buffer += data
                logger.debug(f"Received data: {repr(buffer)}")
                buffer_lower = buffer.lower()
                for prompt in prompts:
                    if prompt.lower() in buffer_lower:
                        logger.debug(f"Found prompt: {prompt}")
                        return buffer
            except socket.timeout:
                continue
            except Exception as e:
                logger.debug(f"Exception reading data: {e}")
                break
        logger.debug(f"Timeout waiting for prompts. Received: {repr(buffer)}")
        raise WattBoxTimeoutError(f"Timeout waiting for prompts: {prompts}. Received: {repr(buffer)}")

    def _send_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        Send a command to the WattBox and return the response.
        
        Args:
            command: Command to send
            timeout: Command-specific timeout
            
        Returns:
            Response from device
        """
        if not self._connection or not self._authenticated:
            raise WattBoxConnectionError("Not connected or authenticated")
        
        timeout = timeout or self.timeout
        formatted_command = format_command(command)
        
        # Use lock to prevent simultaneous commands that could mix responses
        with self._command_lock:
            try:
                logger.debug(f"Sending command: {formatted_command.strip()}")
                
                # Clear any buffered data before sending new command
                self._clear_input_buffer()
                
                # Send command
                self._send_raw(formatted_command)
                
                # Add a longer delay to let the device process the command
                time.sleep(0.1)
                
                # Read response
                response_str = self._read_until_newline(timeout)
                
                logger.debug(f"Received response: {response_str}")
                
                # Validate response based on command type
                is_query_command = formatted_command.strip().startswith('?')
                is_control_command = formatted_command.strip().startswith('!')
                
                if is_query_command:
                    # Query commands should return responses that start with the command prefix
                    expected_prefix = formatted_command.strip().split('=')[0] if '=' in formatted_command else formatted_command.strip()
                    if not response_str.startswith(expected_prefix):
                        logger.warning(f"Response mismatch for query: sent '{expected_prefix}' but got '{response_str[:50]}...'")
                        # Try to read additional data to find the correct response
                        for attempt in range(3):
                            additional_response = self._read_until_newline(1.0)  # Short timeout
                            if additional_response.startswith(expected_prefix):
                                response_str = additional_response
                                logger.debug(f"Found correct response on attempt {attempt + 1}: {response_str}")
                                break
                            elif not additional_response:
                                break
                elif is_control_command:
                    # Control commands should return success/error responses like "OK" or "ERROR"
                    # This is the expected behavior, so no warning needed
                    pass
                
                # Check for error response
                if is_error_response(response_str):
                    raise WattBoxCommandError(f"Command failed: {response_str}")
                
                return response_str
                
            except socket.timeout:
                raise WattBoxTimeoutError(f"Command timeout: {command}")
            except (WattBoxTimeoutError, WattBoxCommandError):
                raise
            except Exception as e:
                raise WattBoxCommandError(f"Command failed: {e}")
    
    # Device Information Methods
    
    def get_device_info(self, refresh: bool = False, include_outlet_power: bool = True) -> WattBoxDevice:
        """
        Get complete device information.
        
        Args:
            refresh: Force refresh of cached data
            include_outlet_power: Include individual outlet power data (may take longer)
        """
        if self._device_info and not refresh:
            return self._device_info
        
        logger.debug("Starting device info collection")
        
        # Get system info
        system_info = self.get_system_info()
        logger.debug("Got system info")
        
        # Get outlet information (including power data if requested)
        # No artificial delay - the API handles response timing naturally
        outlets = self.get_all_outlets_info(include_power_data=include_outlet_power)
        logger.debug("Got outlets info")
        
        # Get power status (if supported)
        logger.debug("Attempting to get power status")
        power_status = self.get_power_status()  # Now returns Optional[PowerStatus]
        logger.debug(f"Got power status: {power_status}")
        
        # Get UPS status (if applicable)
        logger.debug("Attempting to get UPS connection status")
        ups_connected = self.get_ups_connection_status()
        logger.debug(f"UPS connected: {ups_connected}")
        
        ups_status = None
        if ups_connected:
            try:
                logger.debug("Attempting to get UPS status")
                ups_status = self.get_ups_status()
                logger.debug(f"Got UPS status: {ups_status}")
            except WattBoxCommandError:
                logger.debug("UPS status command failed")
                pass
        
        # Get auto reboot status
        logger.debug("Attempting to get auto reboot status")
        auto_reboot_enabled = self.get_auto_reboot_status()
        logger.debug(f"Auto reboot enabled: {auto_reboot_enabled}")
        
        self._device_info = WattBoxDevice(
            system_info=system_info,
            outlets=outlets,
            power_status=power_status,
            ups_status=ups_status,
            ups_connected=ups_connected,
            auto_reboot_enabled=auto_reboot_enabled
        )
        
        logger.debug("Device info collection complete")
        return self._device_info
    
    def get_system_info(self) -> SystemInfo:
        """Get device system information."""
        firmware = self._send_command(WattBoxEndpoints.FIRMWARE)
        hostname = self._send_command(WattBoxEndpoints.HOSTNAME)
        service_tag = self._send_command(WattBoxEndpoints.SERVICE_TAG)
        model = self._send_command(WattBoxEndpoints.MODEL)
        outlet_count_resp = self._send_command(WattBoxEndpoints.OUTLET_COUNT)
        
        # Parse responses
        firmware_val = firmware.split("=")[1] if "=" in firmware else firmware
        hostname_val = hostname.split("=")[1] if "=" in hostname else hostname
        service_tag_val = service_tag.split("=")[1] if "=" in service_tag else service_tag
        model_val = model.split("=")[1] if "=" in model else model
        
        # Handle outlet count parsing with error handling
        try:
            if "=" in outlet_count_resp:
                count_str = outlet_count_resp.split("=")[1].split(",")[0].strip()
                outlet_count_val = int(count_str)
            else:
                outlet_count_val = 0
        except (ValueError, IndexError) as err:
            logger.warning(f"Failed to parse outlet count from '{outlet_count_resp}': {err}")
            # If we can't parse outlet count, try to extract from model name
            # WattBox model names often contain outlet count (e.g., WB-800-IPVM-12 = 12 outlets)
            outlet_count_val = self._extract_outlet_count_from_model(outlet_count_resp, model_val)
            
        # Cache values
        self._outlet_count = outlet_count_val
        self._model = model_val
        self._firmware = firmware_val
        
        return SystemInfo(
            firmware=firmware_val,
            hostname=hostname_val,
            service_tag=service_tag_val,
            model=model_val,
            outlet_count=outlet_count_val
        )
    
    def _extract_outlet_count_from_model(self, outlet_count_response: str, model_name: str) -> int:
        """Extract outlet count from model name when direct parsing fails."""
        import re
        
        # Try to find a number at the end of the response (common pattern)
        # Examples: WB-800-IPVM-12 -> 12, WB-300-IPV-8 -> 8
        for text in [outlet_count_response, model_name]:
            if text:
                # Look for number at the end of string
                match = re.search(r'-(\d+)$', text)
                if match:
                    return int(match.group(1))
                
                # Look for any number in the string as fallback
                numbers = re.findall(r'\d+', text)
                if numbers:
                    # Take the last number found, often the outlet count
                    return int(numbers[-1])
        
        # If we can't determine outlet count, try to get it by querying actual outlets
        return self._determine_outlet_count_by_testing()
    
    def _determine_outlet_count_by_testing(self) -> int:
        """Determine outlet count by testing outlet status queries."""
        # Start with a reasonable default and test up to find the max
        max_test = 20  # Most WattBox units have 12 outlets or fewer
        
        try:
            # Get outlet status which should contain all outlets
            response = self._send_command(WattBoxEndpoints.OUTLET_STATUS)
            if response:
                # Count the number of outlet statuses returned
                # Format is typically like "OutletStatus=1,0,1,0,1" etc.
                if "=" in response:
                    status_part = response.split("=")[1]
                    outlets = status_part.split(",")
                    return len(outlets)
        except Exception:
            pass
        
        # Fallback to a reasonable default
        return 8  # Common outlet count for many WattBox models

    # Outlet Management Methods
    
    def get_outlet_count(self) -> int:
        """Get number of outlets on device."""
        if self._outlet_count is not None:
            return self._outlet_count
        
        try:
            response = self._send_command(WattBoxEndpoints.OUTLET_COUNT)
            logger.debug(f"Outlet count response: {response}")
            if "=" in response:
                count_str = response.split("=")[1].split(",")[0].strip()
                count = int(count_str)
            else:
                count = 0
            self._outlet_count = count
            return count
        except (ValueError, IndexError) as err:
            logger.warning(f"Failed to parse outlet count: {err}")
            # Try to determine outlet count by testing
            count = self._determine_outlet_count_by_testing()
            self._outlet_count = count
            return count
    
    def get_outlet_status(self) -> List[bool]:
        """Get status of all outlets."""
        try:
            response = self._send_command(WattBoxEndpoints.OUTLET_STATUS)
            logger.debug(f"get_outlet_status command: {WattBoxEndpoints.OUTLET_STATUS}, response: {response}")
            return parse_outlet_status_response(response)
        except ValueError as e:
            # If we get the wrong response, try a small delay and retry once
            logger.warning(f"Got unexpected response for outlet status: {e}")
            time.sleep(0.5)  # Small delay to let device settle
            try:
                response = self._send_command(WattBoxEndpoints.OUTLET_STATUS)
                logger.debug(f"get_outlet_status retry command: {WattBoxEndpoints.OUTLET_STATUS}, response: {response}")
                return parse_outlet_status_response(response)
            except ValueError:
                # If still failing, return empty list to prevent crashes
                logger.error(f"Failed to get outlet status after retry, returning empty list")
                return []
    
    def get_outlet_names(self) -> List[str]:
        """Get names of all outlets."""
        response = self._send_command(WattBoxEndpoints.OUTLET_NAMES)
        return parse_outlet_names_response(response)
    
    def get_outlet_power_status(self, outlet: int) -> Optional[OutletInfo]:
        """Get power status for specific outlet."""
        outlet_count = self.get_outlet_count()
        if not validate_outlet_number(outlet, outlet_count):
            raise ValueError(f"Invalid outlet number: {outlet}")
        
        try:
            command = WattBoxEndpoints.outlet_power_status(outlet)
            response = self._send_command(command)
            return parse_outlet_power_response(response)
        except (ValueError, IndexError) as err:
            # Some WattBox devices may not support individual outlet power monitoring
            logger.debug(f"Outlet {outlet} power status not supported or failed: {err}")
            return None
    
    def get_all_outlets_info(self, include_power_data: bool = False) -> List[OutletInfo]:
        """
        Get complete information for all outlets.
        
        Args:
            include_power_data: If True, also collect power data for each outlet
        """
        outlet_count = self.get_outlet_count()
        
        # Try to get outlet statuses and names, but return empty list if they're unavailable
        try:
            outlet_statuses = self.get_outlet_status()
        except Exception as e:
            logger.error(f"Failed to get outlet statuses: {e}")
            return []  # Return empty list to indicate unavailable
        
        try:
            outlet_names = self.get_outlet_names()
        except Exception as e:
            logger.warning(f"Failed to get outlet names: {e}")
            outlet_names = [f"Outlet {i+1}" for i in range(outlet_count)]  # Default names only
        
        # Get power data for all outlets if requested
        power_data = {}
        if include_power_data:
            logger.debug("Including power data in outlet info collection")
            power_data = self.get_all_outlets_power_data()
        
        outlets = []
        
        for i in range(outlet_count):
            outlet_num = i + 1
            
            # Get basic info
            status = outlet_statuses[i] if i < len(outlet_statuses) else False
            name = outlet_names[i] if i < len(outlet_names) else f"Outlet {outlet_num}"
            
            # Get power info if available
            power_watts = None
            current_amps = None
            voltage_volts = None
            
            if include_power_data and outlet_num in power_data and power_data[outlet_num]:
                outlet_power = power_data[outlet_num]
                power_watts = outlet_power.power_watts
                current_amps = outlet_power.current_amps
                voltage_volts = outlet_power.voltage_volts
            
            outlet_info = OutletInfo(
                index=outlet_num,
                name=name,
                status=status,
                power_watts=power_watts,
                current_amps=current_amps,
                voltage_volts=voltage_volts
            )
            
            outlets.append(outlet_info)
        
        return outlets
    
    def set_outlet(self, outlet: int, action: Union[str, OutletAction], delay: Optional[int] = None) -> bool:
        """Control an outlet."""
        outlet_count = self.get_outlet_count()
        if outlet != 0 and not validate_outlet_number(outlet, outlet_count):
            raise ValueError(f"Invalid outlet number: {outlet}")
        
        if isinstance(action, OutletAction):
            action = action.value
        
        if action not in {"ON", "OFF", "TOGGLE", "RESET"}:
            raise ValueError(f"Invalid action: {action}")
        
        command = WattBoxEndpoints.outlet_set(outlet, action, delay)
        response = self._send_command(command)
        return is_success_response(response)
    
    def turn_on_outlet(self, outlet: int) -> bool:
        """Turn on specific outlet."""
        return self.set_outlet(outlet, OutletAction.ON)
    
    def turn_off_outlet(self, outlet: int) -> bool:
        """Turn off specific outlet."""
        return self.set_outlet(outlet, OutletAction.OFF)
    
    def toggle_outlet(self, outlet: int) -> bool:
        """Toggle specific outlet."""
        return self.set_outlet(outlet, OutletAction.TOGGLE)
    
    def reset_outlet(self, outlet: int, delay: Optional[int] = None) -> bool:
        """Reset specific outlet."""
        return self.set_outlet(outlet, OutletAction.RESET, delay)
    
    def reset_all_outlets(self, delay: Optional[int] = None) -> bool:
        """Reset all outlets."""
        return self.set_outlet(0, OutletAction.RESET, delay)
    
    # Power Status Methods
    
    def get_power_status(self) -> Optional[PowerStatus]:
        """Get system power status."""
        try:
            response = self._send_command(WattBoxEndpoints.POWER_STATUS)
            return parse_power_status_response(response)
        except (ValueError, IndexError) as err:
            # Some WattBox devices may not support the PowerStatus command
            logger.debug(f"PowerStatus command not supported or failed: {err}")
            return None
    
    def get_all_outlets_power_data(self, command_timeout: float = 5.0) -> Dict[int, Optional[OutletInfo]]:
        """
        Get power data for all outlets in a single bulk operation.
        
        This method optimizes communication by sending the next request immediately
        after receiving a response, rather than using fixed delays.
        
        Args:
            command_timeout: Timeout for individual outlet queries in seconds
            
        Returns:
            Dictionary mapping outlet index to OutletInfo with power data, or None if unavailable
        """
        logger.debug("Starting optimized bulk outlet power data collection")
        power_data = {}
        
        try:
            outlet_count = self.get_outlet_count()
            logger.debug(f"Collecting power data for {outlet_count} outlets")
            
            for outlet_num in range(1, outlet_count + 1):
                try:
                    start_time = time.time()
                    logger.debug(f"Getting power data for outlet {outlet_num}")
                    outlet_power = self.get_outlet_power_status(outlet_num)
                    power_data[outlet_num] = outlet_power
                    
                    elapsed = time.time() - start_time
                    if outlet_power:
                        logger.debug(f"Outlet {outlet_num} power: {outlet_power.power_watts}W, {outlet_power.current_amps}A, {outlet_power.voltage_volts}V (took {elapsed:.2f}s)")
                    else:
                        logger.debug(f"Outlet {outlet_num} power data not available (took {elapsed:.2f}s)")
                        
                except Exception as e:
                    logger.warning(f"Failed to get power data for outlet {outlet_num}: {e}")
                    power_data[outlet_num] = None
                
                # No artificial delay - the next command will be sent immediately
                # after the response is received and processed
            
            logger.debug(f"Completed optimized bulk power data collection for {len(power_data)} outlets")
            return power_data
            
        except Exception as e:
            logger.error(f"Error during bulk power data collection: {e}")
            return {}
    
    # UPS Methods
    
    def get_ups_connection_status(self) -> bool:
        """Check if UPS is connected."""
        try:
            response = self._send_command(WattBoxEndpoints.UPS_CONNECTION)
            logger.debug(f"UPS connection response: {response}")
            status = response.split("=")[1] if "=" in response else "0"
            # Ensure we only get the first value if there are multiple comma-separated values
            status = status.split(",")[0].strip()
            return bool(int(status))
        except (ValueError, IndexError) as err:
            logger.warning(f"Failed to parse UPS connection status: {err}")
            return False
    
    def get_ups_status(self) -> UPSStatus:
        """Get UPS status information."""
        response = self._send_command(WattBoxEndpoints.UPS_STATUS)
        return parse_ups_status_response(response)
    
    # Auto Reboot Methods
    
    def get_auto_reboot_status(self) -> bool:
        """Get auto reboot status."""
        try:
            response = self._send_command(WattBoxEndpoints.AUTO_REBOOT)
            logger.debug(f"Auto reboot response: {response}")
            status = response.split("=")[1] if "=" in response else "0"
            # Ensure we only get the first value if there are multiple comma-separated values
            status = status.split(",")[0].strip()
            return bool(int(status))
        except (ValueError, IndexError) as err:
            logger.warning(f"Failed to parse auto reboot status: {err}")
            return False
    
    def set_auto_reboot(self, enabled: bool) -> bool:
        """Enable or disable auto reboot."""
        command = WattBoxEndpoints.auto_reboot_set(enabled)
        response = self._send_command(command)
        return is_success_response(response)
    
    # System Control Methods
    
    def reboot_device(self) -> bool:
        """Reboot the WattBox device."""
        response = self._send_command(WattBoxEndpoints.REBOOT, timeout=60.0)
        return is_success_response(response)
    
    # Utility Methods
    
    def is_connected(self) -> bool:
        """Check if client is connected and authenticated."""
        return self._connection is not None and self._authenticated
    
    def ping(self) -> bool:
        """Test connection to the device with a simple command."""
        try:
            # Send a simple command to test connectivity
            response = self._send_command(WattBoxEndpoints.MODEL)
            return bool(response)
        except Exception:
            return False

    def get_model(self) -> str:
        """Get device model."""
        if self._model is not None:
            return self._model
        
        response = self._send_command(WattBoxEndpoints.MODEL)
        model = response.split("=")[1] if "=" in response else response
        self._model = model
        return model
    
    def get_firmware_version(self) -> str:
        """Get firmware version."""
        if self._firmware is not None:
            return self._firmware
        
        response = self._send_command(WattBoxEndpoints.FIRMWARE)
        firmware = response.split("=")[1] if "=" in response else response
        self._firmware = firmware
        return firmware
    
    def _read_available_data(self, timeout: float = 2.0) -> str:
        """Read all available data from the connection."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        
        buffer = b""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                self._connection.settimeout(0.1)
                data = self._connection.recv(1024)
                if not data:
                    break
                buffer += data
            except socket.timeout:
                # No more data available, break
                break
            except Exception:
                break
        
        return buffer.decode('utf-8', errors='ignore')

    def _wait_for_prompt(self, prompt: bytes, timeout: Optional[float] = None) -> bytes:
        """Wait for a specific prompt and return the full response."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        
        if timeout is None:
            timeout = self.timeout
        
        buffer = b""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                self._connection.settimeout(0.1)  # Short timeout for recv
                data = self._connection.recv(1024)
                if not data:
                    break
                buffer += data
                if prompt in buffer:
                    return buffer
            except socket.timeout:
                continue
            except Exception:
                break
        
        raise WattBoxTimeoutError(f"Timeout waiting for prompt: {prompt}")

    def _send_raw(self, data: str) -> None:
        """Send raw data to the connection."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        self._connection.sendall(data.encode())

    def _read_until_newline(self, timeout: Optional[float] = None) -> str:
        """Read response until newline."""
        if not self._connection:
            raise WattBoxConnectionError("Not connected")
        
        if timeout is None:
            timeout = self.timeout
        
        buffer = b""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                self._connection.settimeout(0.1)
                data = self._connection.recv(1)
                if not data:
                    break
                buffer += data
                if data == b"\n":
                    break
            except socket.timeout:
                continue
            except Exception:
                break
        
        return buffer.decode('utf-8', errors='ignore').strip()

    def _clear_input_buffer(self) -> None:
        """Clear any buffered input data to prevent command/response mismatches."""
        if not self._connection:
            return
            
        try:
            # Set a very short timeout to quickly drain any buffered data
            original_timeout = self._connection.gettimeout()
            self._connection.settimeout(0.01)
            
            drained_data = b""
            while True:
                try:
                    data = self._connection.recv(1024)
                    if not data:
                        break
                    drained_data += data
                    # Limit how much we drain to prevent infinite loops
                    if len(drained_data) > 4096:
                        break
                except socket.timeout:
                    # No more data to read
                    break
                except Exception:
                    break
            
            # Restore original timeout
            if original_timeout is not None:
                self._connection.settimeout(original_timeout)
            
            if drained_data:
                logger.debug(f"Cleared {len(drained_data)} bytes from input buffer: {drained_data[:100]}...")
                
        except Exception as e:
            logger.debug(f"Error clearing input buffer: {e}")
