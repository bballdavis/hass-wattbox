# PyWattBox 800

A Python client library for controlling SnapAV WattBox power distribution units using the Integration Protocol v2.4.

## Overview

PyWattBox 800 provides a simple, robust Python interface for communicating with SnapAV WattBox devices over Telnet or SSH connections. This library supports comprehensive outlet control, power monitoring, UPS status, and device management capabilities.

## Features

- **Complete Device Control**: Turn outlets on/off, toggle, reset with optional delays
- **Optimized Power Monitoring**: Get real-time power consumption data with bulk operations optimized for performance
- **Intelligent Device Compatibility**: Gracefully handles devices with varying feature support (WB150/250 vs WB800+ series)
- **UPS Integration**: Monitor UPS status including battery health, charge level, and runtime
- **Auto Reboot Management**: Configure and monitor automatic reboot functionality
- **Device Information**: Access firmware version, model, hostname, and service tag with automatic fallback mechanisms
- **Network Discovery**: Scan for WattBox devices on your network
- **Enhanced Error Handling**: Comprehensive error handling with device-specific capability detection
- **Robust Communication**: Built-in authentication, response validation, and connection management
- **Context Manager Support**: Clean resource management with automatic connection cleanup
- **Performance Optimized**: Bulk operations use immediate response processing without artificial delays

## Supported WattBox Models

This library supports all WattBox 800 series models and intelligently adapts to device capabilities:

- **WB-800-IPVM series** (12+ outlet models) - Full feature support including individual outlet power monitoring
- **WB-150/250 series** - Basic outlet control (power monitoring features automatically disabled)
- **Any WattBox model supporting Integration Protocol v2.4**
- **Connection Types**: Both Telnet (port 23) and SSH (port 22) connections
- **Firmware Support**: All versions, with SSH requiring firmware 1.3.0.4+
- **Automatic Feature Detection**: Library automatically detects and adapts to device capabilities

## Installation

Currently, this library is not published to PyPI. Clone the repository and install locally:

```bash
git clone https://github.com/your-username/pywattbox_800.git
cd pywattbox_800
pip install -e .
```

### Dependencies

- Python 3.7+
- No external dependencies (uses only Python standard library)

## Quick Start

### Basic Usage

```python
from pywattbox_800 import WattBoxClient

# Connect to your WattBox device
with WattBoxClient(host="192.168.1.100", username="wattbox", password="wattbox") as client:
    # Get device information
    device_info = client.get_device_info()
    print(f"Connected to {device_info.system_info.model}")
    print(f"Firmware: {device_info.system_info.firmware}")
    print(f"Outlets: {device_info.system_info.outlet_count}")
    
    # Control outlets
    client.turn_on_outlet(1)    # Turn on outlet 1
    client.turn_off_outlet(2)   # Turn off outlet 2
    client.toggle_outlet(3)     # Toggle outlet 3
    client.reset_outlet(4, delay=5)  # Reset outlet 4 with 5-second delay
    
    # Get outlet status
    outlets = client.get_all_outlets_info(include_power_data=True)
    for outlet in outlets:
        print(f"Outlet {outlet.index}: {outlet.name} - {'ON' if outlet.status else 'OFF'}")
        if outlet.power_watts:
            print(f"  Power: {outlet.power_watts}W, {outlet.current_amps}A, {outlet.voltage_volts}V")
```

### Power Monitoring

```python
with WattBoxClient(host="192.168.1.100") as client:
    # Get system-wide power status (if supported by device)
    power_status = client.get_power_status()
    if power_status:
        print(f"Total Power: {power_status.power_watts}W")
        print(f"Total Current: {power_status.current_amps}A")
        print(f"Voltage: {power_status.voltage_volts}V")
        print(f"Safe Voltage: {power_status.safe_voltage_status}")
    else:
        print("Power monitoring not supported on this device")
    
    # Get individual outlet power data
    outlet_power = client.get_outlet_power_status(1)
    if outlet_power:
        print(f"Outlet 1 Power: {outlet_power.power_watts}W")
        print(f"Outlet 1 Current: {outlet_power.current_amps}A")
        print(f"Outlet 1 Voltage: {outlet_power.voltage_volts}V")
    else:
        print("Individual outlet power monitoring not supported")
    
    # Bulk power data collection (optimized for performance)
    all_power_data = client.get_all_outlets_power_data()
    for outlet_num, power_info in all_power_data.items():
        if power_info:
            print(f"Outlet {outlet_num}: {power_info.power_watts}W")
```

### UPS Monitoring

```python
with WattBoxClient(host="192.168.1.100") as client:
    # Check if UPS is connected
    if client.get_ups_connection_status():
        ups_status = client.get_ups_status()
        print(f"Battery Charge: {ups_status.battery_charge}%")
        print(f"Battery Load: {ups_status.battery_load}%")
        print(f"Battery Health: {ups_status.battery_health}")
        print(f"Runtime Remaining: {ups_status.battery_runtime} minutes")
        print(f"Power Lost: {ups_status.power_lost}")
        print(f"Alarm Enabled: {ups_status.alarm_enabled}")
        print(f"Alarm Muted: {ups_status.alarm_muted}")
    else:
        print("No UPS connected to this device")
```

### Device Discovery

```python
from pywattbox_800.utils import discover_wattbox_devices

# Scan for WattBox devices on your network
devices = discover_wattbox_devices(subnet="192.168.1")
print(f"Found WattBox devices at: {devices}")
```

### Advanced Usage

### Custom Authentication and Timeouts

```python
client = WattBoxClient(
    host="192.168.1.100",
    port=23,                    # 23 for Telnet, 22 for SSH
    username="admin",
    password="your_password", 
    timeout=15.0,              # Command timeout in seconds
    connection_type="telnet"   # "telnet" or "ssh"
)
```

### Performance Monitoring

```python
import time

with WattBoxClient(host="192.168.1.100") as client:
    # Time bulk power data collection
    start_time = time.time()
    power_data = client.get_all_outlets_power_data()
    elapsed = time.time() - start_time
    
    outlet_count = len([p for p in power_data.values() if p is not None])
    print(f"Collected power data for {outlet_count} outlets in {elapsed:.2f}s")
    
    # Compare with individual calls (slower)
    start_time = time.time()
    for outlet_num in range(1, client.get_outlet_count() + 1):
        power_info = client.get_outlet_power_status(outlet_num)
    elapsed_individual = time.time() - start_time
    
    print(f"Individual calls took {elapsed_individual:.2f}s")
    print(f"Bulk operation is {elapsed_individual/elapsed:.1f}x faster")
```

### Device Capability Testing

```python
with WattBoxClient(host="192.168.1.100") as client:
    # Test what features are available
    device_info = client.get_device_info(include_outlet_power=False)  # Faster initial check
    
    print(f"Device: {device_info.system_info.model}")
    print(f"Outlets: {device_info.system_info.outlet_count}")
    
    # Test power monitoring capability
    power_status = client.get_power_status()
    if power_status:
        print("✓ System power monitoring supported")
    else:
        print("✗ System power monitoring not available")
    
    # Test individual outlet power monitoring
    first_outlet_power = client.get_outlet_power_status(1)
    if first_outlet_power:
        print("✓ Individual outlet power monitoring supported")
    else:
        print("✗ Individual outlet power monitoring not available")
    
    # Test UPS features
    if client.get_ups_connection_status():
        print("✓ UPS connected and monitoring available")
        ups_status = client.get_ups_status()
        print(f"  Battery: {ups_status.battery_charge}% ({ups_status.battery_health})")
    else:
        print("✗ No UPS connected")
```

### Bulk Operations

```python
with WattBoxClient(host="192.168.1.100") as client:
    # Get all outlet information with optimized power data collection
    outlets = client.get_all_outlets_info(include_power_data=True)
    for outlet in outlets:
        status = "ON" if outlet.status else "OFF"
        print(f"Outlet {outlet.index}: {outlet.name} - {status}")
        if outlet.power_watts is not None:
            print(f"  Power: {outlet.power_watts}W, {outlet.current_amps}A, {outlet.voltage_volts}V")
    
    # Bulk power monitoring (performance optimized)
    power_data = client.get_all_outlets_power_data()
    total_power = sum(info.power_watts for info in power_data.values() if info and info.power_watts)
    print(f"Total system power consumption: {total_power}W")
    
    # Control multiple outlets
    for outlet_num in range(1, 5):  # Turn on outlets 1-4
        client.turn_on_outlet(outlet_num)
    
    # Reset all outlets with delay
    client.reset_all_outlets(delay=10)
```

### Auto Reboot Configuration

```python
with WattBoxClient(host="192.168.1.100") as client:
    # Enable auto reboot
    client.set_auto_reboot(True)
    
    # Check auto reboot status
    enabled = client.get_auto_reboot_status()
    print(f"Auto reboot enabled: {enabled}")
```

## API Reference

### WattBoxClient

The main client class for communicating with WattBox devices.

#### Constructor

```python
WattBoxClient(host, port=23, username="wattbox", password="wattbox", timeout=10.0, connection_type="telnet")
```

#### Device Information Methods

- `get_device_info(refresh=False, include_outlet_power=True)` - Get complete device state
- `get_system_info()` - Get system information (model, firmware, etc.)
- `get_model()` - Get device model
- `get_firmware_version()` - Get firmware version

#### Outlet Control Methods

- `get_outlet_count()` - Get number of outlets
- `get_outlet_status()` - Get status of all outlets
- `get_outlet_names()` - Get names of all outlets
- `get_all_outlets_info(include_power_data=False)` - Get complete outlet information
- `set_outlet(outlet, action, delay=None)` - Control outlet (action: "ON", "OFF", "TOGGLE", "RESET")
- `turn_on_outlet(outlet)` - Turn on specific outlet
- `turn_off_outlet(outlet)` - Turn off specific outlet
- `toggle_outlet(outlet)` - Toggle specific outlet
- `reset_outlet(outlet, delay=None)` - Reset specific outlet
- `reset_all_outlets(delay=None)` - Reset all outlets

#### Power Monitoring Methods

- `get_power_status()` - Get system-wide power status (returns `None` if not supported)
- `get_outlet_power_status(outlet)` - Get power status for specific outlet (returns `None` if not supported)
- `get_all_outlets_power_data(command_timeout=5.0)` - Get power data for all outlets (optimized bulk operation)

#### UPS Methods

- `get_ups_connection_status()` - Check if UPS is connected
- `get_ups_status()` - Get UPS status information

#### Auto Reboot Methods

- `get_auto_reboot_status()` - Get auto reboot status
- `set_auto_reboot(enabled)` - Enable/disable auto reboot

#### Utility Methods

- `connect()` - Establish connection
- `disconnect()` - Close connection
- `is_connected()` - Check connection status
- `ping()` - Test device connectivity
- `reboot_device()` - Reboot the WattBox device

### Data Models

#### WattBoxDevice
Complete device state containing system info, outlets, power status, and UPS status.

#### OutletInfo
Information about a specific outlet including name, status, and power data.

#### PowerStatus
System-wide power status with current, power, voltage, and safety status.

#### UPSStatus
UPS status including battery charge percentage, battery load, health status, power lost status, runtime in minutes, and alarm settings.

#### SystemInfo
Device system information including firmware, hostname, service tag, and model.

### Exceptions

- `WattBoxError` - Base exception for all WattBox errors
- `WattBoxConnectionError` - Connection-related errors
- `WattBoxAuthenticationError` - Authentication failures
- `WattBoxCommandError` - Command execution errors
- `WattBoxTimeoutError` - Timeout errors
- `WattBoxResponseError` - Unexpected response errors

## Performance Optimizations

The library includes several performance optimizations:

### Bulk Power Data Collection
The `get_all_outlets_power_data()` method has been optimized to eliminate artificial delays:
- Commands are sent immediately after receiving responses
- No fixed delays between outlet queries
- Significantly faster bulk operations
- Efficient for monitoring multiple outlets

### Response Validation
- Automatic retry logic for mismatched responses
- Input buffer clearing to prevent command/response mix-ups
- Enhanced response validation with error recovery

### Device Capability Detection
- Automatic detection of device features (power monitoring, UPS, etc.)
- Graceful fallback for unsupported features
- Prevents unnecessary command timeouts on incompatible devices

## Protocol Support

This library implements the SnapAV WattBox Integration Protocol v2.4, supporting:

- **Authentication**: Username/password login
- **Command Types**: Query (?), Control (!), Error (#), Unsolicited (~)
- **Connection Types**: Telnet (port 23), SSH (port 22, firmware 1.3.0.4+)
- **Response Parsing**: Automatic parsing of all response formats

## Error Handling

The library includes comprehensive error handling with automatic device capability detection:

```python
from pywattbox_800 import WattBoxClient, WattBoxConnectionError, WattBoxAuthenticationError

try:
    with WattBoxClient(host="192.168.1.100") as client:
        # Get device info - automatically handles missing features
        device_info = client.get_device_info()
        print(f"Connected to {device_info.system_info.model}")
        
        # Power monitoring - gracefully handles unsupported devices
        power_status = client.get_power_status()
        if power_status:
            print(f"Power monitoring: {power_status.power_watts}W")
        else:
            print("Power monitoring not available on this device")
        
        # Outlet control - always supported
        client.turn_on_outlet(1)
        
except WattBoxConnectionError:
    print("Failed to connect to device - check IP address and network")
except WattBoxAuthenticationError:
    print("Invalid credentials - check username and password")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Automatic Feature Detection
The library automatically detects device capabilities:
- **Power Monitoring**: Detects if `PowerStatus` and `OutletPowerStatus` are supported
- **UPS Features**: Checks for UPS connection before querying status
- **Outlet Count**: Uses multiple methods to determine the correct outlet count
- **Error Recovery**: Retries commands with improved response matching

## Logging

Enable debug logging to see detailed communication and performance metrics:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Example debug output:
# DEBUG:pywattbox_800.client:Sending command: ?OutletPowerStatus=1
# DEBUG:pywattbox_800.client:Received response: ?OutletPowerStatus=1,1.01,0.02,116.50
# DEBUG:pywattbox_800.client:Outlet 1 power: 1.01W, 0.02A, 116.50V (took 0.15s)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SnapAV for the WattBox Integration Protocol v2.4 specification
- The WattBox community for testing and feedback

## Support

For issues and questions:
1. Check the [API documentation](wattbox_api_v2.4.md) for protocol details
2. Review the examples in this README
3. Open an issue on GitHub with detailed information about your setup and the problem

## Changelog

### v2.4.0
- **Performance Optimizations**: Bulk power data collection now uses immediate response processing
- **Enhanced Device Compatibility**: Automatic detection and graceful handling of device capabilities
- **Improved Error Handling**: Better response validation, retry logic, and error recovery
- **Optional Feature Support**: Power monitoring and UPS features return `None` when not supported
- **Enhanced Logging**: Comprehensive debug logging with performance metrics
- **Better Response Handling**: Input buffer clearing and response synchronization
- **Context Manager Support**: Full support for `with` statements and automatic cleanup
- **Network Discovery**: Added `discover_wattbox_devices()` utility function
- **Robust Communication**: Enhanced authentication and connection management