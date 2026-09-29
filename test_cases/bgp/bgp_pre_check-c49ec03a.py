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

class CollectBgpStateAcrossAllAddressFamilies(aetest.Testcase):
    @aetest.test
    def collect_bgp_state_across_all_address_families(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        overall_failed = False

        for device in devices:
            device_name = getattr(device, "name", str(device))
            print(json.dumps({"netvalid_device_started": {"device": device_name}}))

            try:
                device.connect(via="cli")
            except Exception as exc:
                overall_failed = True
                logger.warning("Failed to connect to %s: %s", device_name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"connect failed: {exc}"
                    }
                }))
                continue

            try:
                state = device.learn("bgp")
                parsed = getattr(state, "info", state)

                if parsed is None:
                    parsed = {}
                if not isinstance(parsed, dict):
                    parsed = {"value": parsed}

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device_name,
                        "key": "bgp",
                        "parsed": parsed,
                        "exclude": []
                    }
                }, default=str))

                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "pass",
                        "detail": "BGP state learned across all address families"
                    }
                }))
            except Exception as exc:
                overall_failed = True
                logger.warning("Failed to learn BGP state on %s: %s", device_name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"BGP learn failed: {exc}"
                    }
                }))

        if overall_failed:
            self.failed("One or more devices failed to collect BGP state")
        else:
            self.passed("BGP state collected for all devices")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)