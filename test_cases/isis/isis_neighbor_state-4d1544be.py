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

class CollectIsisNeighborState(aetest.Testcase):
    @aetest.test
    def collect_isis_neighbor_state(self):
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
            print(json.dumps({"netvalid_device_started": {"device": device.name}}))

            try:
                device.connect(via="cli")
            except Exception as exc:
                failed_devices.append(device.name)
                logger.warning("Failed to connect to %s: %s", device.name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "error",
                        "detail": f"connect failed: {exc}"
                    }
                }))
                continue

            try:
                # device.parse("show isis neighbors") is used deliberately
                # instead of device.learn("isis"): the latter invokes several
                # underlying "show isis ..." sub-commands, some of whose
                # parsers (in genie.libs.parser.iosxr.show_isis) don't match
                # this platform's real CLI output and crash before returning
                # anything at all (verified empirically against real
                # hardware). "show isis neighbors" alone is a clean, minimal
                # parser that returns exactly the adjacency state that
                # actually matters for a baseline check (is the session up),
                # without pulling in the fragile statistics/log sub-parsers.
                parsed = device.parse("show isis neighbors")
                if not isinstance(parsed, dict):
                    parsed = {}

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device.name,
                        "key": "isis_neighbors",
                        "parsed": parsed
                    }
                }, default=str))

                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "pass",
                        "detail": "ISIS neighbor state collected"
                    }
                }))
            except Exception as exc:
                failed_devices.append(device.name)
                logger.warning("Failed to collect ISIS neighbor state on %s: %s", device.name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "error",
                        "detail": f"ISIS neighbor collection failed: {exc}"
                    }
                }))

        if failed_devices:
            self.failed("ISIS neighbor state collection failed for devices: " + ", ".join(failed_devices))
        else:
            self.passed("ISIS neighbor state collected for all devices")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)
