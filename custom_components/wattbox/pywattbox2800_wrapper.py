"""
pywattbox2800_wrapper.py

A compatibility wrapper that adapts the pywattbox (HTTP API) client to the v2.4-style interface expected by the integration.
"""

from custom_components.wattbox.pywattbox.http_wattbox import HttpWattBox

class PyWattBox2800Wrapper:
    def __init__(self, host, username, password, port=80, **kwargs):
        self._client = HttpWattBox(host, username, password, port)
        self._client.get_initial()

    def get_device_info(self, refresh=False, include_outlet_power=True):
        return {
            'system_info': {
                'model': self._client.hardware_version,
                'firmware': self._client.firmware_version,
                'hostname': self._client.hostname,
                'outlet_count': self._client.number_outlets,
                'serial_number': self._client.serial_number,
            },
            'outlets': [
                {
                    'index': o.index,
                    'name': o.name,
                    'status': o.status,
                    'power_watts': o.power_value,
                    'current_amps': o.current_value,
                    'voltage_volts': o.voltage_value,
                } for o in self._client.outlets.values()
            ],
            'power_status': self.get_power_status(),
            'ups_status': self.get_ups_status() if self.get_ups_connection_status() else None,
        }

    def get_system_info(self):
        return {
            'model': self._client.hardware_version,
            'firmware': self._client.firmware_version,
            'hostname': self._client.hostname,
            'serial_number': self._client.serial_number,
        }

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
        from custom_components.wattbox.pywattbox.base import Commands
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
        o = self._client.outlets[outlet]
        return {
            'power_watts': o.power_value,
            'current_amps': o.current_value,
            'voltage_volts': o.voltage_value,
        }

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
        self._client.get_initial()

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
