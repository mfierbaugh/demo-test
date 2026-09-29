import os
import sys
import json
import logging
from pyats import aetest
from pyats.topology import loader

logger = logging.getLogger(__name__)

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass

class CollectIsisStateAcrossAddressFamilies(aetest.Testcase):
    @aetest.test
    def test_collect_isis_state(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices_obj = getattr(testbed, "devices", {}) or {}
        devices = list(devices_obj.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        errors = []
        successes = 0

        for device in devices:
            device_name = getattr(device, "name", str(device))
            print(json.dumps({"netvalid_device_started": {"device": device_name}}, default=str))

            try:
                device.connect(via="cli")
                state = device.learn("isis")
                parsed = getattr(state, "info", state)

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device_name,
                        "key": "isis",
                        "parsed": parsed,
                        "exclude": []
                    }
                }, default=str))

                successes += 1
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "pass",
                        "detail": "ISIS state learned across all address families"
                    }
                }, default=str))

            except Exception as exc:
                logger.warning("Failed to collect ISIS state on %s: %s", device_name, exc)
                errors.append(device_name)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"Failed to collect ISIS state: {exc}"
                    }
                }, default=str))

        if errors:
            self.failed(f"Failed to collect ISIS state from devices: {', '.join(errors)}")
        elif successes == 0:
            self.failed("No ISIS state collected from any device")
        else:
            self.passed(f"Collected ISIS state from {successes} device(s) across all address families")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)