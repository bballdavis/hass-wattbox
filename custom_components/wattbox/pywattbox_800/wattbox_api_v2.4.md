# SnapAV WattBox Integration Protocol v2.4

## Overview

This integration protocol details how a third-party system can be used to control a SnapAV WattBox. The WattBox listens for connections on:
- **Port 23** (Telnet)
- **Port 22** (SSH, requires firmware 1.3.0.4+)

## Important Information

- **SSH Support**: Added with firmware 1.3.0.4
- **Connection Limit**: Maximum 10 simultaneous connections
- **SSH Password Limit**: 13 characters maximum for SSH credentials

## Authentication

The protocol requires authentication before proceeding with commands. Upon connection:
1. A login prompt is received
2. Provide valid username and password
3. If correct, login succeeds and commands can be issued
4. If incorrect, login prompt is shown again

## Message Structure

Commands and responses use standard ASCII text with the following prefixes:

| Prefix | Type | Description |
|--------|------|-------------|
| `?` | Request | Request information from device |
| `!` | Control | Send control commands to device |
| `#` | Error | Error response from device |
| `~` | Unsolicited | Unsolicited messages from device |
| `\n` | Terminator | End of command (ASCII 0x0A) |

## API Endpoints

### Device Information

#### Get Firmware Version
```
Request:  ?Firmware\n
Response: ?Firmware=1.0.0.0\n
```

#### Get Hostname
```
Request:  ?Hostname\n
Response: ?Hostname=Wattbox\n
```

#### Get Service Tag
```
Request:  ?ServiceTag\n
Response: ?ServiceTag=ST191500681E8422\n
```

#### Get Model Number
```
Request:  ?Model\n
Response: ?Model=WB-800-IPVM-6\n
```

### Outlet Management

#### Get Outlet Count
```
Request:  ?OutletCount\n
Response: ?OutletCount=16\n
```

#### Get All Outlet Status
```
Request:  ?OutletStatus\n
Response: ?OutletStatus=0,0,0,0,0,0,0,0,0,0,0,0\n
```
- Array index = outlet number
- Value: `0` = off, `1` = on

#### Get Specific Outlet Power Status
```
Request:  ?OutletPowerStatus=OUTLET\n
Response: ?OutletPowerStatus=1,1.01,0.02,116.50\n
```
**Note**: Not supported on WB150/250

**Response Format**:
- `1` = outlet index requested
- `1.01` = power in watts
- `0.02` = current in amps  
- `116.50` = voltage in volts

#### Get All Outlet Names
```
Request:  ?OutletName\n
Response: ?OutletName={Outlet 1},{Outlet 2},{Outlet 3},{Outlet 4},{Outlet 5},{Outlet 6},{Outlet 7},{Outlet 8},{Outlet 9},{Outlet 10},{Outlet 11},{Outlet 12}\n
```

#### Set Single Outlet Name
```
Request:  !OutletNameSet=OUTLET,NAME\n
Response: OK\n
```

#### Set All Outlet Names
```
Request:  !OutletNameSetAll={NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME},{NAME}\n
Response: OK\n
```

#### Control Outlet
```
Request:  !OutletSet=OUTLET,ACTION,DELAY\n
Response: OK\n
```

**Parameters**:
- `OUTLET`: Outlet number (0 = all outlets for RESET)
- `ACTION`: `ON`, `OFF`, `TOGGLE`, `RESET`
- `DELAY`: Optional delay for RESET (1-600 seconds)

#### Set Outlet Power On Delay
```
Request:  !OutletPowerOnDelaySet=OUTLET,DELAY\n
Response: OK\n
```
- `DELAY`: 1-600 seconds

#### Set Outlet Mode
```
Request:  !OutletModeSet=OUTLET,MODE\n
Response: OK\n
```

**Modes**:
- `0` = Enabled
- `1` = Disabled  
- `2` = Reset Only

#### Set Outlet Reboot Operation
```
Request:  !OutletRebootSet=OP,OP,OP,OP,OP,OP,OP,OP,OP,OP,OP,OP\n
Response: OK\n
```

**Operations**:
- `0` = Any selected hosts timeout (OR)
- `1` = All selected hosts timeout (AND)

### System Power Status

#### Get System Power Status
```
Request:  ?PowerStatus\n
Response: ?PowerStatus=60.00,600.00,110.00,1\n
```
**Note**: Not supported on WB150/250

**Response Format**:
- `60.00` = current in amps
- `600.00` = power in watts
- `110.00` = voltage in volts
- `1` = safe voltage status

### Auto Reboot

#### Get Auto Reboot Status
```
Request:  ?AutoReboot\n
Response: ?AutoReboot=1\n
```
- `1` = Enabled
- `0` = Disabled

#### Set Auto Reboot
```
Request:  !AutoReboot=STATE\n
Response: OK\n
```
- `STATE`: `1` = enabled, `0` = disabled

#### Set Auto Reboot Timeout Settings
```
Request:  !AutoRebootTimeoutSet=TIMEOUT,COUNT,PING_DELAY,REBOOT_ATTEMPTS\n
Response: OK\n
```

**Parameters**:
- `TIMEOUT`: 1-60 seconds (timeout before considering host down)
- `COUNT`: 1-10 (consecutive timeouts before reboot)
- `PING_DELAY`: 1-30 minutes (delay before retesting after reboot)
- `REBOOT_ATTEMPTS`: 0-10 (0 = unlimited)

### UPS Status (if applicable)

#### Get UPS Status
```
Request:  ?UPSStatus\n
Response: ?UPSStatus=50,0,Good,False,25,True,False\n
```

**Response Format**:
- `50` = battery charge percentage (0-100%)
- `0` = battery load percentage (0-100%)
- `Good` = battery health (Good/Bad)
- `False` = power lost status (True/False)
- `25` = battery runtime in minutes
- `True` = alarm enabled (True/False)
- `False` = alarm muted (True/False)

#### Get UPS Connection Status
```
Request:  ?UPSConnection\n
Response: ?UPSConnection=0\n
```
- `0` = Disconnected
- `1` = Connected

### Host Monitoring

#### Add Host
```
Request:  !HostAdd=NAME,IP,{OUTLET,OUTLET}\n
Response: OK\n
```
- `NAME`: Host name
- `IP`: Website or IP address to monitor
- `{OUTLET,OUTLET}`: Array of outlet numbers to control

### Scheduling

#### Add Schedule
```
Request:  !ScheduleAdd={NAME},{OUTLET,OUTLET,OUTLET},{ACTION},{FREQ},{DAY,DAY,DAY | DATE},{TIME}\n
Response: OK\n
```

**Parameters**:
- `{NAME}`: Schedule name
- `{OUTLET,OUTLET,OUTLET}`: Array of outlet numbers
- `{ACTION}`: `0` = Off, `1` = On, `2` = Reset
- `{FREQ}`: `0` = Once, `1` = Recurring
- `{DAY,DAY,DAY}`: For recurring (0=exclude, 1=include) [Sun,Mon,Tue,Wed,Thu,Fri,Sat]
- `{DATE}`: For once (yyyy/mm/dd format)
- `{TIME}`: 24-hour format (hh:mm)

### System Settings

#### Set Account Credentials
```
Request:  !AccountSet=USER,PASS\n
Response: OK\n
```
**Note**: Connection will be lost and reconnection required

#### Set Network Configuration
```
Request:  !NetworkSet=HOST,IP,SUBNET,GATEWAY,DNS1,DNS2\n
Response: OK\n
```

**DHCP**: Send only `HOST`
**Static**: `HOST,IP,SUBNET,GATEWAY,DNS1` required, `DNS2` optional

#### Enable/Disable Telnet
```
Request:  !SetTelnet=MODE\n
Response: OK\n
```
- `MODE`: `0` = disabled, `1` = enabled
- **Note**: Reboot required

#### Enable/Disable Web Server
```
Request:  !WebServerSet=MODE\n
Response: OK\n
```
- `MODE`: `0` = disabled, `1` = enabled
- **Note**: Requires firmware 2.0+, reboot required

#### Enable/Disable SDDP Broadcasting
```
Request:  !SetSDDP=MODE\n
Response: OK\n
```
- `MODE`: `0` = disabled, `1` = enabled
- **Note**: Requires firmware 2.0+

### System Control

#### Firmware Update
```
Request:  !FirmwareUpdate=URL\n
Response: OK\n
```
**Note**: System shuts down immediately, connection lost

#### Reboot Device
```
Request:  !Reboot\n
Response: OK\n
```
**Note**: Connection lost until device comes back online

#### Exit Session
```
Request:  !Exit\n
```
Closes the session gracefully

### Error Handling

#### Error Response
```
Response: #Error\n
```
Sent when:
- Invalid command received
- Internal device error occurred
- Check device log page for detailed error messages

## Integration Notes for 800 Series

### Required Endpoints for Home Assistant Integration
- `?OutletCount` - Dynamic outlet discovery
- `?OutletStatus` - Current outlet states
- `?OutletName` - Outlet naming
- `?OutletPowerStatus=X` - Per-outlet power monitoring
- `?PowerStatus` - System power status
- `!OutletSet=OUTLET,ACTION` - Outlet control
- `?UPSStatus` - UPS monitoring (if applicable)
- `?Model` - Device identification
- `?Firmware` - Version information

### Not Required for Basic Integration
- Scheduling commands
- Network configuration
- Account management
- Host monitoring
- Firmware updates
- Service enable/disable commands

## Authentication Flow

1. Connect to device on port 23 (Telnet) or 22 (SSH)
2. Receive login prompt
3. Send username
4. Send password
5. If successful, begin sending commands
6. Use `!Exit` to close session gracefully

## Error Codes

- `#Error\n` - Generic error response
- Check device web interface logs for detailed error information
