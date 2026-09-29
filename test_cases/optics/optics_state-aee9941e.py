import os
import sys
from pyats import aetest
from pyats.topology import loader
import json
import logging

logger = logging.getLogger(__name__)


def _print_json(payload):
    try:
        print(json.dumps(payload, default=str))
        return True
    except Exception:
        try:
            print(json.dumps(payload, default=str, skipkeys=True))
            return True
        except Exception:
            print(json.dumps({
                "netvalid_print_error": {
                    "detail": "Failed to serialize JSON payload"
                }
            }, default=str))
            return False


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass


class CollectShowControllerOptics(aetest.Testcase):
    @aetest.test
    def collect_show_controller_optics(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        successes = 0
        failures = 0

        for device in devices:
            device_name = getattr(device, "name", str(device))

            _print_json({
                "netvalid_device_started": {
                    "device": device_name
                }
            })

            try:
                device.connect(via="cli")
                parsed = device.parse("show controller optics *")

                baseline_ok = _print_json({
                    "netvalid_baseline_state": {
                        "device": device_name,
                        "key": "show controller optics",
                        "parsed": parsed,
                        "exclude": [],
                    }
                })

                if not baseline_ok:
                    _print_json({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "fail",
                            "detail": "Failed to serialize show controller optics state",
                        }
                    })
                    failures += 1
                    continue

                if parsed is None:
                    _print_json({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "fail",
                            "detail": "show controller optics returned no parsed data",
                        }
                    })
                    failures += 1
                else:
                    _print_json({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "pass",
                            "detail": "show controller optics parsed and reported for baseline comparison",
                        }
                    })
                    successes += 1

            except Exception as exc:
                logger.warning(
                    "Failed to collect show controller optics on %s: %s",
                    device_name,
                    exc,
                )
                _print_json({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"Failed to collect show controller optics: {exc}",
                    }
                })
                failures += 1

        if failures > 0:
            self.failed("One or more devices failed to collect show controller optics")
        else:
            self.passed("Collected show controller optics from all %d device(s)" % successes)


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass


if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)