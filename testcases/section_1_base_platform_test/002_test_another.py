import sys
from pyats import aetest

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass

class TestShowPlatform(aetest.Testcase):
    @aetest.test
    def get_show_platform(self):
        devices = self.parameters.get('devices', [])

        if isinstance(devices, dict):
            devices = list(devices.values())
        elif not isinstance(devices, (list, tuple)):
            devices = [devices] if devices else []

        if not devices:
            device = self.parameters.get('device')
            if device:
                devices = [device]

        if not devices:
            testbed = getattr(self, 'testbed', None)
            if testbed is not None:
                devices = list(getattr(testbed, 'devices', {}).values())

        if not devices:
            self.failed('No devices available to run show platform')
            return

        failures = []

        for device in devices:
            device_name = getattr(device, 'name', str(device))

            try:
                output = device.parse('show platform')
            except Exception as exc:
                failures.append(f'{device_name}: {exc}')
                continue

            if not output:
                failures.append(f'{device_name}: show platform returned no parsed output')

        if failures:
            self.failed('Failed to get show platform from devices: ' + '; '.join(failures))
        else:
            self.passed('show platform retrieved successfully from all devices')

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    result = aetest.main()
    sys.exit(0 if result else 1)