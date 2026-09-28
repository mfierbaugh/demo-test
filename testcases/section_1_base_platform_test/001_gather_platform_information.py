import sys
from pyats import aetest


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass


class VerifyPlatformAndVersion(aetest.Testcase):
    @aetest.test
    def verify_platform_and_version(self):
        device = getattr(self, "device", None)

        if device is None:
            testbed = getattr(self, "testbed", None)
            devices = getattr(testbed, "devices", None) if testbed is not None else None
            if devices:
                device = list(devices.values())[0]

        if device is None:
            self.failed("No device available to execute show platform and show version")
            return

        try:
            if hasattr(device, "parse"):
                platform_output = device.parse("show platform")
                version_output = device.parse("show version")
            else:
                platform_output = device.execute("show platform")
                version_output = device.execute("show version")
        except Exception as exc:
            self.failed(f"Failed to execute show platform or show version: {exc}")
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
            "show platform and show version executed successfully; "
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
    result = aetest.main()
    sys.exit(0 if result else 1)