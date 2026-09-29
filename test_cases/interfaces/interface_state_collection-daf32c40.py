import os
import sys
from pyats import aetest
from pyats.topology import loader
import json
import logging

logger = logging.getLogger(__name__)

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass

class CollectInterfaceState(aetest.Testcase):
    @aetest.test
    def collect_interface_state(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        failed_devices = []

        for device in devices:
            print(json.dumps({"netvalid_device_started": {"device": device.name}}, default=str))
            try:
                device.connect(via="cli")
                state = device.learn("interface")
                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device.name,
                        "key": "interface",
                        "parsed": state.info,
                        "exclude": []
                    }
                }, default=str))
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "pass",
                        "detail": "Interface state learned successfully"
                    }
                }, default=str))
            except Exception as exc:
                logger.warning("Failed to learn interface state on %s: %s", device.name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "error",
                        "detail": f"Failed to learn interface state: {exc}"
                    }
                }, default=str))
                failed_devices.append(device.name)

        if failed_devices:
            self.failed("Interface state collection failed for devices: " + ", ".join(failed_devices))
        else:
            self.passed("Interface state collected for all devices")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)