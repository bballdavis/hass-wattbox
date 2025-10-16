# WattBox API v2.0 Documentation

This document describes the HTTP API for controlling outlets and retrieving status from WattBox 300 and 700 series devices.

## Overview
The WattBox API v2.0 allows you to control outlets (on, off, reset, auto reboot) and retrieve device status using HTTP requests. All requests require HTTP Basic Authentication.

---

## 1. Control Outlet Command

**Request Format:**
```
GET /control.cgi?outlet=<OUTLET_NUMBER>&command=<COMMAND_NUMBER> HTTP/1.1
Host: <WattBox_IP>
Keep-Alive: 300
Connection: keep-alive
Authorization: Basic <base64-encoded-credentials>
User-Agent: APP
```

**Parameters:**
- `<OUTLET_NUMBER>`: Outlet to control. Use `0` to select all outlets (reset only). Example ranges:
  - WB-300-IP-3: 0–3
  - WB-700-IPV-12: 0–12
- `<COMMAND_NUMBER>`:
  - `0`: Power off
  - `1`: Power on
  - `3`: Power reset (only if outlet is already on)
  - `4`: Auto reboot on
  - `5`: Auto reboot off

**Example:**
To reset outlet 1:
```
GET /control.cgi?outlet=1&command=3 HTTP/1.1
...headers as above...
```

**Authorization:**
Base64 encode `username:password` and use as the value for the `Authorization: Basic` header.
Example: `admin:1234` → `YWRtaW46MTIzNA==`

---

## 2. Control Outlet Response

**Response Format (XML):**

### WB-300-IP-3
```xml
<?xml version='1.0'?>
<request>
  <outlet_status>{OUTLET1},{OUTLET2},{OUTLET3}</outlet_status>
  <auto_reboot>{AUTO_REBOOT}</auto_reboot>
</request>
```

### WB-700-IPV-12
```xml
<?xml version='1.0'?>
<request>
  <outlet_status>{OUTLET1},{OUTLET2},...,{OUTLET12}</outlet_status>
  <auto_reboot>{AUTO_REBOOT}</auto_reboot>
</request>
```

**Notes:**
- `{OUTLET#}`: 0 = off, 1 = on
- `{AUTO_REBOOT}`: 0 = off, 1 = on

---

## 3. Get Status Command

**Request Format:**
```
GET /wattbox_info.xml HTTP/1.1
Host: <WattBox_IP>
...headers as above...
```

---

## 4. Get Status Response

**Response Format (XML):**

### WB-300-IP-3
```xml
<?xml version='1.0'?>
<request>
  <host_name>{HOST_NAME}</host_name>
  <hardware_version>WB-300-IP-3</hardware_version>
  <serial_number>{SERIAL_NUMBER}</serial_number>
  <site_ip>{SITE_IP1},{SITE_IP2},{SITE_IP3},{SITE_IP4},{SITE_IP5},{SITE_IP6},{SITE_IP7}</site_ip>
  <connect_status>{C1_S},{C2_S},{C3_S},{C4_S},{C5_S},{C6_S},{C7_S}</connect_status>
  <site_lost>{S1_L},{S2_L},{S3_L},{S4_L},{S5_L},{S6_L},{S7_L}</site_lost>
  <auto_reboot>{A_R}</auto_reboot>
  <outlet_name>{OUTLET_NAME1},{OUTLET_NAME2},{OUTLET_NAME3}</outlet_name>
  <outlet_status>{O1_S},{O2_S},{O3_S}</outlet_status>
  <outlet_mode>{O1_M},{O2_M},{O3_M}</outlet_mode>
  <led_status>{L_I},{L_S},{L_A}</led_status>
  <safe_voltage_status>{SAFE_VOLTAGE_STATUS}</safe_voltage_status>
  <voltage_value>{VOLTAGE_VALUE}</voltage_value>
  <current_value>{CURRENT_VALUE}</current_value>
  <power_value>{POWER_VALUE}</power_value>
</request>
```

### WB-700-IPV-12
```xml
<?xml version='1.0'?>
<request>
  <host_name>{HOST_NAME}</host_name>
  <hardware_version>WB-700-IPV-12</hardware_version>
  <serial_number>{SERIAL_NUMBER}</serial_number>
  <site_ip>{SITE_IP1},...,{SITE_IP16}</site_ip>
  <connect_status>{C1_S},...,{C16_S}</connect_status>
  <site_lost>{S1_L},...,{S16_L}</site_lost>
  <auto_reboot>{A_R}</auto_reboot>
  <outlet_name>{OUTLET_NAME1},...,{OUTLET_NAME12}</outlet_name>
  <outlet_status>{O1_S},...,{O12_S}</outlet_status>
  <outlet_mode>{O1_M},...,{O12_M}</outlet_mode>
  <led_status>{L_I},{L_S},{L_A}</led_status>
  <safe_voltage_status>{SAFE_VOLTAGE_STATUS}</safe_voltage_status>
  <voltage_value>{VOLTAGE_VALUE}</voltage_value>
  <current_value>{CURRENT_VALUE}</current_value>
  <power_value>{POWER_VALUE}</power_value>
</request>
```

---

## 5. Field Descriptions

- **HOST_NAME**: Name of the WattBox (max 32 chars)
- **SERIAL_NUMBER**: Serial number (max 10 chars)
- **SITE_IP#**: IP address of connectivity test site
- **C#_S**: Connectivity site response time (ms)
- **S#_L**: Ping loss percentage for each site
- **A_R**: Auto-reboot (0 = off, 1 = on)
- **OUTLET_NAME#**: Name of outlet
- **O#_S**: Outlet status (0 = off, 1 = on)
- **O#_M**:
  - WB-300-IP-3: 1 = normal, 2 = reset only
  - WB-700-IPV-12: 0 = master switch disabled, 1 = enabled, 2 = disabled/reset only
- **L_I / L_S / L_A**: LED status (0 = off, 1 = green, 2 = red, 3 = green blinking, 4 = red blinking)
- **SAFE_VOLTAGE_STATUS**: 0 = SVC off, 1 = on/safe, 2 = on/unsafe
- **VOLTAGE_VALUE**: Voltage in tenths of a volt (e.g., 1115 = 111.5V)
- **CURRENT_VALUE**: Current in tenths of an amp (e.g., 105 = 10.5A)
- **POWER_VALUE**: Power in watts (e.g., 600 = 600W)

---

## 6. Notes
- All requests require HTTP Basic Authentication.
- All responses are in XML format.
- The API is supported on both WB-300-IP-3 and WB-700-IPV-12 models.
