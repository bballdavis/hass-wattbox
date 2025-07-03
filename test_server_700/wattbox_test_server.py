import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

USERNAME = "wattbox"
PASSWORD = "wattbox"
PORT = 80

# Simulate a WB-700-IPV-12 (12 outlets)
NUM_OUTLETS = 12

class WattBoxHandler(BaseHTTPRequestHandler):
    outlet_status = [1] * NUM_OUTLETS  # All on by default
    auto_reboot = 0
    outlet_names = [f"Outlet {i+1}" for i in range(NUM_OUTLETS)]

    def do_GET(self):
        if not self.check_auth():
            self.send_auth_required()
            return

        parsed = urlparse(self.path)
        if parsed.path == "/control.cgi":
            self.handle_control(parsed)
        elif parsed.path == "/wattbox_info.xml":
            self.handle_status()
        else:
            self.send_error(404, "Not Found")

    def check_auth(self):
        auth = self.headers.get('Authorization')
        if not auth or not auth.startswith('Basic '):
            return False
        encoded = auth.split(' ', 1)[1]
        try:
            decoded = base64.b64decode(encoded).decode()
        except Exception:
            return False
        return decoded == f"{USERNAME}:{PASSWORD}"

    def send_auth_required(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="WattBox"')
        self.end_headers()
        self.wfile.write(b'Authentication required.')

    def handle_control(self, parsed):
        qs = parse_qs(parsed.query)
        try:
            outlet = int(qs.get('outlet', [None])[0])
            command = int(qs.get('command', [None])[0])
        except (TypeError, ValueError):
            self.send_error(400, "Invalid parameters")
            return
        # Command logic
        if outlet == 0 and command == 3:
            # Reset all outlets
            for i in range(NUM_OUTLETS):
                if self.outlet_status[i] == 1:
                    self.outlet_status[i] = 0
                    self.outlet_status[i] = 1
        elif 1 <= outlet <= NUM_OUTLETS:
            idx = outlet - 1
            if command == 0:
                self.outlet_status[idx] = 0
            elif command == 1:
                self.outlet_status[idx] = 1
            elif command == 3:
                if self.outlet_status[idx] == 1:
                    self.outlet_status[idx] = 0
                    self.outlet_status[idx] = 1
            elif command == 4:
                self.auto_reboot = 1
            elif command == 5:
                self.auto_reboot = 0
        # Respond
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml')
        self.end_headers()
        xml = f'''<?xml version='1.0'?>
<request>
  <outlet_status>{','.join(str(x) for x in self.outlet_status)}</outlet_status>
  <auto_reboot>{self.auto_reboot}</auto_reboot>
</request>'''
        self.wfile.write(xml.encode())

    def handle_status(self):
        # Example values for other fields
        host_name = "TestWattBox700"
        hardware_version = "WB-700-IPV-12"
        serial_number = "1234567890"
        site_ip = ",".join([f"192.168.1.{i+1}" for i in range(16)])
        connect_status = ",".join(["10"]*16)
        site_lost = ",".join(["0"]*16)
        outlet_names = ",".join(self.outlet_names)
        outlet_status = ",".join(str(x) for x in self.outlet_status)
        outlet_mode = ",".join(["1"]*NUM_OUTLETS)
        led_status = "1,1,1"
        safe_voltage_status = "1"
        voltage_value = "1200"
        current_value = "100"
        power_value = "600"
        xml = f'''<?xml version='1.0'?>
<request>
  <host_name>{host_name}</host_name>
  <hardware_version>{hardware_version}</hardware_version>
  <serial_number>{serial_number}</serial_number>
  <site_ip>{site_ip}</site_ip>
  <connect_status>{connect_status}</connect_status>
  <site_lost>{site_lost}</site_lost>
  <auto_reboot>{self.auto_reboot}</auto_reboot>
  <outlet_name>{outlet_names}</outlet_name>
  <outlet_status>{outlet_status}</outlet_status>
  <outlet_mode>{outlet_mode}</outlet_mode>
  <led_status>{led_status}</led_status>
  <safe_voltage_status>{safe_voltage_status}</safe_voltage_status>
  <voltage_value>{voltage_value}</voltage_value>
  <current_value>{current_value}</current_value>
  <power_value>{power_value}</power_value>
</request>'''
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml')
        self.end_headers()
        self.wfile.write(xml.encode())

if __name__ == "__main__":
    server = HTTPServer(("", PORT), WattBoxHandler)
    print(f"WattBox 700 Test Server running on port {PORT}")
    server.serve_forever()
