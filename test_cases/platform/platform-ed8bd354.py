import os
import sys
import json
import logging
import re
from pyats import aetest
from pyats.topology import loader

logger = logging.getLogger(__name__)


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass


class VerifyShowPlatformNoFailedComponents(aetest.Testcase):
    @aetest.test
    def verify_show_platform_no_failed_components(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices defined in testbed")
            return

        bad_key_words = (
            "failed",
            "failure",
            "failures",
            "error",
            "errors",
            "fault",
            "faults",
            "faulty",
            "bad",
            "not_ok",
            "not ok",
        )

        status_keys = {
            "status",
            "state",
            "oper_state",
            "operstate",
            "operational_state",
            "operational_status",
            "health",
            "health_state",
            "result",
            "error_state",
            "fault_state",
            "component_status",
            "card_status",
            "power_status",
            "power_supply_status",
            "fan_status",
            "temperature_status",
            "led_status",
            "software_status",
            "hardware_status",
            "state_machine",
        }

        bad_exact = {
            "failed",
            "failure",
            "failures",
            "error",
            "errors",
            "fault",
            "faults",
            "faulty",
            "bad",
            "not ok",
            "down",
        }

        bad_word_regex = re.compile(
            r"\b(failed|failures?|faults?|faulty|bad|not ok|down)\b",
            re.IGNORECASE,
        )

        negation_regex = re.compile(
            r"\b(not|no|without)\b.*\b(failed|failures?|faults?|faulty|bad|down)\b",
            re.IGNORECASE,
        )

        def _is_bad_status(value):
            if isinstance(value, bool):
                return False
            if isinstance(value, (int, float)):
                return False
            if not isinstance(value, str):
                return False

            norm = value.strip().lower()
            if not norm:
                return False

            core = norm.strip(" .,;:?!")
            if core in bad_exact:
                return True

            if negation_regex.search(norm):
                return False

            for bad in (
                "failed",
                "failure",
                "failures",
                "fault",
                "faults",
                "faulty",
                "bad",
                "not ok",
                "down",
            ):
                if (
                    norm.startswith(bad + " ")
                    or norm.startswith(bad + ",")
                    or norm.startswith(bad + ";")
                    or norm.startswith(bad + ":")
                    or norm.startswith(bad + ".")
                    or norm.startswith(bad + "?")
                ):
                    return True

            if bad_word_regex.search(norm):
                return True

            return False

        def _get_name(container):
            if not isinstance(container, dict):
                return None

            for key in (
                "name",
                "component",
                "card",
                "node",
                "slot",
                "id",
                "description",
                "label",
                "power_supply",
                "fan",
                "led",
                "sensor",
            ):
                if key in container:
                    val = container[key]
                    if isinstance(val, (str, int, float)) and not isinstance(val, bool):
                        return str(val)

            return None

        def _find_failed(parsed):
            failed = []
            seen = set()

            def _add(path, value, name=None):
                key = (path, str(value), name)
                if key in seen:
                    return
                seen.add(key)
                failed.append({"path": path, "value": value, "name": name})

            def _walk(obj, path):
                if isinstance(obj, dict):
                    name = _get_name(obj)

                    for k, v in obj.items():
                        key_norm = str(k).lower()
                        is_bad_key = any(word in key_norm for word in bad_key_words)

                        if is_bad_key:
                            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                                _add(path + (str(k),), v, name)
                            elif isinstance(v, str):
                                norm = v.strip().lower()
                                if norm.isdigit() and int(norm) > 0:
                                    _add(path + (str(k),), v, name)
                                elif norm in {"yes", "true", "1"}:
                                    _add(path + (str(k),), v, name)
                                elif _is_bad_status(v):
                                    _add(path + (str(k),), v, name)

                        if key_norm in status_keys:
                            if _is_bad_status(v):
                                _add(path + (str(k),), v, name)
                            elif isinstance(v, list):
                                for item in v:
                                    if _is_bad_status(item):
                                        _add(path + (str(k),), item, name)

                        _walk(v, path + (str(k),))

                elif isinstance(obj, list):
                    for idx, item in enumerate(obj):
                        _walk(item, path + (str(idx),))

            _walk(parsed, ())
            return failed

        def _format_detail(failed):
            if not failed:
                return "no failed components"

            count = len(failed)
            examples = []

            for item in failed[:3]:
                name = item.get("name")
                if name:
                    label = str(name)
                else:
                    path = item.get("path", ())
                    label = " -> ".join(str(p) for p in path[-4:])

                examples.append(f"{label}={item.get('value')}")

            detail = f"{count} failed component(s): " + "; ".join(examples)
            if count > 3:
                detail += f" (+{count - 3} more)"

            return detail

        any_failed = False
        any_error = False

        for device in devices:
            device_name = str(getattr(device, "name", device))

            try:
                device.connect(via="cli")
                parsed = device.parse("show platform")

                if parsed is None:
                    any_error = True
                    print(json.dumps({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "error",
                            "detail": "device.parse returned no data",
                        }
                    }))
                    continue

                print(json.dumps({
                    "netvalid_baseline_state": {
                        "device": device_name,
                        "key": "show platform",
                        "parsed": parsed,
                        "exclude": [],
                    }
                }, default=str))

                failed = _find_failed(parsed)

                if failed:
                    any_failed = True
                    print(json.dumps({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "fail",
                            "detail": _format_detail(failed),
                        }
                    }))
                else:
                    print(json.dumps({
                        "netvalid_device_result": {
                            "device": device_name,
                            "status": "pass",
                            "detail": "no failed components",
                        }
                    }))

            except Exception as exc:
                any_error = True
                logger.warning("Failed to check show platform on %s: %s", device_name, exc)
                print(json.dumps({
                    "netvalid_device_result": {
                        "device": device_name,
                        "status": "error",
                        "detail": f"exception: {exc}",
                    }
                }))

        if any_error or any_failed:
            self.failed("show platform verification failed")
        else:
            self.passed("show platform verification passed")


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass


if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)