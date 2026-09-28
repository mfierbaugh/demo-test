import os
import sys
from pyats import aetest
from pyats.topology import loader


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass


class VerifyPlatformAndVersion(aetest.Testcase):
    @aetest.test
    def verify_platform_and_version(self):
        testbed = self.parameters.get("testbed")
        if testbed is None or not testbed.devices:
            self.failed("No testbed/devices available for this run")
            return

        device = list(testbed.devices.values())[0]

        try:
            device.connect(via="cli", connection_timeout=30, learn_hostname=True)
            platform_output = device.parse("show platform")
            version_output = device.parse("show version")
        except Exception as exc:
            self.failed(f"Failed to connect/execute show platform or show version: {exc}")
            return

        if not version_output:
            self.failed("show version returned no output")
            return

        failed_components = self._find_failed_components(platform_output)

        if failed_components:
            details = "; ".join(failed_components[:20])
            self.failed(f"Platform components in failed state detected: {details}")
            return

        self.passed(
            f"show platform and show version executed successfully on {device.name}; "
            "no failed platform components detected"
        )

    def _find_failed_components(self, data, path="platform"):
        failed = []

        if isinstance(data, dict):
            for key, value in data.items():
                child_path = f"{path}.{key}"
                key_text = str(key).lower()

                if any(token in key_text for token in ("state", "status")):
                    if isinstance(value, str) and value.strip().lower() in ("failed", "fail", "failure"):
                        failed.append(f"{child_path}={value}")

                failed.extend(self._find_failed_components(value, child_path))

        elif isinstance(data, list):
            for index, item in enumerate(data):
                failed.extend(self._find_failed_components(item, f"{path}[{index}]"))

        else:
            text = str(data)
            for line in text.splitlines():
                line_lower = line.lower()
                if "failed" in line_lower and "no failed" not in line_lower:
                    failed.append(line.strip())

        return failed


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass


if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)
