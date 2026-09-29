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

class CaptureShowVersion(aetest.Testcase):
    @aetest.test
    def test_capture_show_version(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        overall_pass = True

        for device in devices:
            try:
                device.connect(via="cli")
                parsed = device.parse("show version")

                if parsed is None:
                    raise ValueError("Parsed output is empty")

                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "pass",
                        "detail": "show version captured"
                    }
                }, default=str))

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device.name,
                        "key": "show version",
                        "parsed": parsed,
                        "exclude": []
                    }
                }, default=str))

            except Exception as exc:
                overall_pass = False
                logger.warning("Failed to capture show version on %s: %s", device.name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device.name,
                        "status": "error",
                        "detail": str(exc)
                    }
                }, default=str))

        if overall_pass:
            self.passed("show version captured for all devices")
        else:
            self.failed("show version capture failed for one or more devices")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)