# PyWattBox (HTTP API, Port 80)

A Python client library for controlling SnapAV WattBox power distribution units using the HTTP API (port 80).

## Overview

PyWattBox provides a Python interface for communicating with SnapAV WattBox devices over HTTP. It supports basic outlet control, power monitoring, UPS status, and device management.

## Features

- **Outlet Control**: Turn outlets on/off, reset, and master switch control
- **Power Monitoring**: Get system-wide and per-outlet power data (if supported)
- **UPS Integration**: Monitor UPS status including battery health, charge, and runtime
- **Device Information**: Access firmware version, model, hostname, and serial number
- **Auto Reboot Management**: Configure and monitor automatic reboot functionality
- **Async and Sync Support**: All major operations are available in both sync and async forms
- **Robust Communication**: Built-in authentication and response validation

## Supported WattBox Models

- All SnapAV WattBox models supporting the HTTP API (typically port 80)
- **Connection Type**: HTTP (port 80)
- **Automatic Feature Detection**: Library detects and adapts to device capabilities

## Installation

Currently, this library is not published to PyPI. Clone the repository and install locally:

```bash
git clone https://github.com/your-username/pywattbox.git
cd pywattbox
pip install -e .
```

### Dependencies

- Python 3.7+
- `httpx`, `beautifulsoup4`

## Quick Start

### Basic Usage

```python
from pywattbox.http_wattbox import HttpWattBox

# Connect to your WattBox device
client = HttpWattBox(host="192.168.1.100", user="wattbox", password="wattbox")
client.get_initial()

# Get device information
print(f"Model: {client.hardware_version}")
print(f"Firmware: {client.firmware_version}")
print(f"Outlets: {client.number_outlets}")

# Control outlets
client.outlets[1].turn_on()    # Turn on outlet 1
client.outlets[2].turn_off()   # Turn off outlet 2
client.outlets[3].reset()      # Reset outlet 3

# Get outlet status
for outlet in client.outlets.values():
    print(f"Outlet {outlet.index}: {outlet.name} - {'ON' if outlet.status else 'OFF'}")
    if outlet.power_value is not None:
        print(f"  Power: {outlet.power_value}W, {outlet.current_value}A, {outlet.voltage_value}V")
```

### Power Monitoring

```python
client.update()
print(f"Total Power: {client.power_value}W")
print(f"Total Current: {client.current_value}A")
print(f"Voltage: {client.voltage_value}V")

# Per-outlet power (if supported)
for outlet in client.outlets.values():
    if outlet.power_value is not None:
        print(f"Outlet {outlet.index} Power: {outlet.power_value}W")
```

### UPS Monitoring

```python
if client.has_ups:
    print(f"Battery Charge: {client.battery_charge}%")
    print(f"Battery Health: {client.battery_health}")
    print(f"Battery Load: {client.battery_load}%")
    print(f"Runtime Remaining: {client.est_run_time} minutes")
else:
    print("No UPS connected to this device")
```

### Master Switch Control

```python
client.master_outlet.turn_on()   # Turn on all outlets
client.master_outlet.turn_off()  # Turn off all outlets
```

## API Reference

### HttpWattBox

The main client class for communicating with WattBox devices over HTTP.

#### Constructor

```python
HttpWattBox(host, user, password, port=80)
```

#### Device Information Methods

- `get_initial()` – Fetch and parse initial device state
- `async_get_initial()` – Async version
- `parse_initial(response)` – Parse device info from HTTP response
- `update()` – Fetch and parse current status
- `async_update()` – Async version
- `parse_update(response)` – Parse status from HTTP response

#### Outlet Control Methods

- `send_command(outlet, command)` – Control a specific outlet (ON, OFF, RESET)
- `async_send_command(outlet, command)` – Async version
- `send_master_command(command)` – Simulate master switch (all outlets)
- `async_send_master_command(command)` – Async version

#### Outlet Data

- `self.outlets` – Dict of `Outlet` objects, indexed by outlet number
- `self.master_outlet` – Special `MasterSwitch` object for all outlets

#### Power Monitoring

- `self.power_value` – System-wide power (watts)
- `self.current_value` – System-wide current (amps)
- `self.voltage_value` – System-wide voltage (volts)
- Per-outlet power data is available via each `Outlet` object (if supported)

#### UPS Methods

- UPS status and battery info are parsed from the XML and stored as attributes:
  - `self.has_ups`, `self.battery_charge`, `self.battery_health`, `self.battery_load`, `self.est_run_time`, etc.

#### Auto Reboot

- `self.auto_reboot` – Boolean, parsed from device

#### Utility

- `__str__()` – String representation

### Outlet
- Represents a single outlet.
- Methods: `turn_on()`, `turn_off()`, `reset()`, and async versions.
- Attributes: `index`, `name`, `status`, `method`, `power_value`, `current_value`, `voltage_value`.

### MasterSwitch
- Special subclass of `Outlet` for master switch operations.

## Exceptions

- Standard Python exceptions (e.g., `ValueError` for invalid commands).

## Logging

Enable debug logging to see detailed communication and performance metrics:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
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

- SnapAV for the WattBox Integration Protocol and HTTP API
- The WattBox community for testing and feedback

## Support

For issues and questions:
1. Review the examples in this README
2. Open an issue on GitHub with detailed information about your setup and the problem

## Changelog

### v1.0.0
- Initial release: HTTP API support, outlet control, power monitoring, UPS support, async/sync methods, master switch control, and logging.
