"""
WattBox HTTP-to-v2.4 Compatibility Wrapper

This class adapts the pywattbox (HTTP API) client to the v2.4-style interface expected by the integration.
- Methods and return values are aligned with the v2.4 API where possible.
- If a method is not available in HTTP, NotImplementedError is raised.
- Extra HTTP-only features are exposed with their native names/format.
"""

from .pywattbox.http_wattbox import HttpWattBox

class PyWattBoxWrapper:
    def __init__(self, host, username, password, port=80, **kwargs):
        self._client = HttpWattBox(host, username, password, port)
        # Add logging before getting initial data
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"PyWattBoxWrapper: Initializing HTTP client for {host}:{port}")
        self._client.get_initial()
        logger.info(f"PyWattBoxWrapper: Initial data retrieved. Number of outlets: {self._client.number_outlets}")
        logger.info(f"PyWattBoxWrapper: Hardware version: {self._client.hardware_version}")
        logger.info(f"PyWattBoxWrapper: Serial number: {self._client.serial_number}")
        logger.info(f"PyWattBoxWrapper: Hostname: {self._client.hostname}")
        if hasattr(self._client, 'outlets') and self._client.outlets:
            logger.info(f"PyWattBoxWrapper: Outlets dict keys: {list(self._client.outlets.keys())}")
            for outlet_id, outlet in self._client.outlets.items():
                logger.info(f"PyWattBoxWrapper: Outlet {outlet_id}: name='{outlet.name}', status={outlet.status}, method={getattr(outlet, 'method', 'N/A')}")
        else:
            logger.warning("PyWattBoxWrapper: No outlets found in client!")

    def get_device_info(self, refresh=False, include_outlet_power=True):
        from .pywattbox_800.models import WattBoxDevice, OutletInfo, SystemInfo, PowerStatus, UPSStatus
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"PyWattBoxWrapper.get_device_info: refresh={refresh}, include_outlet_power={include_outlet_power}")
        
        if refresh:
            logger.info("PyWattBoxWrapper.get_device_info: Refreshing data from device")
            self._client.update()
            
        logger.info(f"PyWattBoxWrapper.get_device_info: Client outlets count: {len(self._client.outlets) if hasattr(self._client, 'outlets') else 'N/A'}")
        logger.info(f"PyWattBoxWrapper.get_device_info: Client number_outlets: {getattr(self._client, 'number_outlets', 'N/A')}")

        outlets = []
        if hasattr(self._client, 'outlets') and self._client.outlets:
            for o in self._client.outlets.values():
                outlet_info = OutletInfo(
                    index=o.index,
                    name=o.name or "Unknown Outlet",
                    status=o.status or False,
                    power_watts=o.power_value,
                    current_amps=o.current_value,
                    voltage_volts=o.voltage_value,
                )
                outlets.append(outlet_info)
                logger.info(f"PyWattBoxWrapper.get_device_info: Created OutletInfo for outlet {o.index}: name='{outlet_info.name}', status={outlet_info.status}")
        else:
            logger.warning("PyWattBoxWrapper.get_device_info: No outlets available in client")

        system_info = SystemInfo(
            model=self._client.hardware_version or "Unknown Model",
            firmware=self._client.firmware_version or "Unknown Firmware",
            hostname=self._client.hostname or "Unknown Hostname",
            service_tag=self._client.serial_number or "Unknown Serial",
            outlet_count=self._client.number_outlets or 0,
        )
        
        logger.info(f"PyWattBoxWrapper.get_device_info: SystemInfo - model={system_info.model}, outlet_count={system_info.outlet_count}")

        power_status = PowerStatus(
            power_watts=self._client.power_value,
            current_amps=self._client.current_value,
            voltage_volts=self._client.voltage_value,
            safe_voltage_status=bool(getattr(self._client, 'safe_voltage_status', False)),
        )

        ups_status = UPSStatus(
            battery_charge=self._client.battery_charge,
            battery_load=self._client.battery_load,
            battery_health=str(self._client.battery_health),
            battery_runtime=self._client.est_run_time,
            power_lost=self._client.power_lost,
            alarm_enabled=bool(getattr(self._client, 'audible_alarm', False)),
            alarm_muted=bool(getattr(self._client, 'mute', False)),
        ) if self.get_ups_connection_status() else None

        device = WattBoxDevice(
            system_info=system_info,
            outlets=outlets,
            power_status=power_status,
            ups_status=ups_status,
            ups_connected=self.get_ups_connection_status(),
            auto_reboot_enabled=self._client.auto_reboot,
        )
        
        logger.info(f"PyWattBoxWrapper.get_device_info: Returning device with {len(outlets)} outlets")
        return device

    def get_system_info(self):
        # Create a simple object that mimics SystemInfo structure
        class SystemInfoCompat:
            def __init__(self, model, firmware, hostname, serial_number, outlet_count):
                self.model = model
                self.firmware = firmware
                self.hostname = hostname
                self.service_tag = serial_number  # Use service_tag to match WattBoxClient
                self.outlet_count = outlet_count
        
        return SystemInfoCompat(
            model=self._client.hardware_version,
            firmware=self._client.firmware_version,
            hostname=self._client.hostname,
            serial_number=self._client.serial_number,
            outlet_count=self._client.number_outlets
        )

    def get_model(self):
        return self._client.hardware_version

    def get_firmware_version(self):
        return self._client.firmware_version

    def get_outlet_count(self):
        return self._client.number_outlets

    def get_outlet_status(self):
        return [o.status for o in self._client.outlets.values()]

    def get_outlet_names(self):
        return [o.name for o in self._client.outlets.values()]

    def get_all_outlets_info(self, include_power_data=False):
        return [
            {
                'index': o.index,
                'name': o.name,
                'status': o.status,
                'power_watts': o.power_value,
                'current_amps': o.current_value,
                'voltage_volts': o.voltage_value,
            } for o in self._client.outlets.values()
        ]

    def set_outlet(self, outlet, action, delay=None):
        from .pywattbox.base import Commands
        cmd = getattr(Commands, action.upper(), None)
        if cmd is None:
            raise ValueError(f"Invalid action: {action}")
        self._client.send_command(outlet, cmd)

    def turn_on_outlet(self, outlet):
        self._client.outlets[outlet].turn_on()

    def turn_off_outlet(self, outlet):
        self._client.outlets[outlet].turn_off()

    def reset_outlet(self, outlet, delay=None):
        self._client.outlets[outlet].reset()

    def reset_all_outlets(self, delay=None):
        if self._client.master_outlet is not None:
            self._client.master_outlet.turn_off()
            self._client.master_outlet.turn_on()
        else:
            raise NotImplementedError("Master switch control is not available on this device/API.")

    def get_power_status(self):
        return {
            'power_watts': self._client.power_value,
            'current_amps': self._client.current_value,
            'voltage_volts': self._client.voltage_value,
            'safe_voltage_status': getattr(self._client, 'safe_voltage_status', None),
        }

    def get_outlet_power_status(self, outlet):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"PyWattBoxWrapper.get_outlet_power_status: Requesting power status for outlet {outlet}")
        
        if outlet not in self._client.outlets:
            logger.warning(f"PyWattBoxWrapper.get_outlet_power_status: Outlet {outlet} not found in client outlets")
            return None
            
        o = self._client.outlets[outlet]
        result = {
            'power_watts': o.power_value,
            'current_amps': o.current_value,
            'voltage_volts': o.voltage_value,
        }
        logger.info(f"PyWattBoxWrapper.get_outlet_power_status: Outlet {outlet} power data: {result}")
        return result

    def get_all_outlets_power_data(self, command_timeout=5.0):
        return {
            o.index: {
                'power_watts': o.power_value,
                'current_amps': o.current_value,
                'voltage_volts': o.voltage_value,
            } for o in self._client.outlets.values()
        }

    def get_ups_connection_status(self):
        return getattr(self._client, 'has_ups', False)

    def get_ups_status(self):
        if not self.get_ups_connection_status():
            return None
        return {
            'battery_charge': self._client.battery_charge,
            'battery_load': self._client.battery_load,
            'battery_health': self._client.battery_health,
            'battery_runtime': self._client.est_run_time,
            'power_lost': self._client.power_lost,
            'alarm_enabled': getattr(self._client, 'audible_alarm', None),
            'alarm_muted': getattr(self._client, 'mute', None),
        }

    def get_auto_reboot_status(self):
        return getattr(self._client, 'auto_reboot', None)

    def set_auto_reboot(self, enabled):
        raise NotImplementedError("Auto reboot configuration is not supported via HTTP API.")

    def connect(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("PyWattBoxWrapper.connect: Refreshing data from device")
        self._client.get_initial()
        logger.info(f"PyWattBoxWrapper.connect: After refresh - Number of outlets: {self._client.number_outlets}")
        if hasattr(self._client, 'outlets') and self._client.outlets:
            logger.info(f"PyWattBoxWrapper.connect: Available outlet indices: {list(self._client.outlets.keys())}")
        else:
            logger.warning("PyWattBoxWrapper.connect: No outlets available after refresh!")

    def disconnect(self):
        pass

    def is_connected(self):
        return True

    def ping(self):
        raise NotImplementedError("Ping is not supported via HTTP API.")

    def reboot_device(self):
        raise NotImplementedError("Device reboot is not supported via HTTP API.")

    def get_http_client(self):
        return self._client

    @property
    def host(self):
        return self._client.host
