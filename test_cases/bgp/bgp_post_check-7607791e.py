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

class CollectBgpStateAllAddressFamilies(aetest.Testcase):
    @aetest.test
    def collect_bgp_state_all_address_families(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices_obj = getattr(testbed, "devices", None)
        devices = list(devices_obj.values()) if devices_obj else []
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
            except Exception as exc:
                errors.append(device_name)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"CLI connect failed: {exc}"
                    }
                }, default=str))
                continue

            try:
                state = device.learn("bgp")
                parsed = getattr(state, "info", {})
                if not isinstance(parsed, dict):
                    parsed = {"info": parsed}

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device_name,
                        "key": "bgp",
                        "parsed": parsed,
                        "exclude": []
                    }
                }, default=str))

                successes += 1
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "pass",
                        "detail": "Learned BGP state across all address families"
                    }
                }, default=str))
            except Exception as exc:
                errors.append(device_name)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"BGP learn failed: {exc}"
                    }
                }, default=str))

        if errors:
            self.failed(f"Failed to collect BGP state on devices: {', '.join(errors)}")
        elif successes:
            self.passed(f"Collected BGP state across all address families on {successes} device(s)")
        else:
            self.failed("No BGP state collected")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)