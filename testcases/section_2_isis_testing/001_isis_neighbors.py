import os
import sys
from pyats import aetest
from pyats.topology import loader

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def setup(self):
        pass

class VerifyIsisNeighborsUp(aetest.Testcase):
    @aetest.test
    def test_verify_isis_neighbors_up(self):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices found in testbed")
            return

        state_keys = ("state", "neighbor_state", "adj_state", "status")
        id_keys = (
            "system_id",
            "sys_id",
            "neighbor_system_id",
            "neighbor",
            "interface",
            "if_name",
            "ifname",
            "instance",
        )
        structural_keys = {
            "info",
            "neighbors",
            "neighbor",
            "data",
            "output",
            "result",
            "parsed",
            "raw",
            "stdout",
            "stderr",
        }

        def _is_neighbor_entry(obj, parent_key=None):
            if not isinstance(obj, dict):
                return False

            keys = {str(k).lower() for k in obj.keys()}
            has_state = any(k in keys for k in state_keys)
            has_id = any(k in keys for k in id_keys)

            if not has_state:
                return False

            if has_id:
                return True

            if parent_key is not None:
                parent = str(parent_key).lower()
                if parent not in structural_keys and len(parent) > 1:
                    return True

            return False

        def _find_neighbor_entries(obj, parent_key=None):
            entries = []

            if isinstance(obj, dict):
                if _is_neighbor_entry(obj, parent_key):
                    entries.append(obj)
                    return entries

                for key, value in obj.items():
                    entries.extend(_find_neighbor_entries(value, key))

            elif isinstance(obj, list):
                for item in obj:
                    entries.extend(_find_neighbor_entries(item, parent_key))

            return entries

        def _stringify(value):
            if isinstance(value, list):
                value = value[0] if value else None

            if isinstance(value, dict):
                value = (
                    value.get("state")
                    or value.get("value")
                    or value.get("neighbor_state")
                    or value.get("adj_state")
                )

            return str(value) if value is not None else None

        def _get_state(entry):
            lower_entry = {str(k).lower(): v for k, v in entry.items()}

            for key in state_keys:
                if key in lower_entry:
                    state = _stringify(lower_entry[key])
                    if state is not None:
                        return state

            def _search(obj):
                found = []

                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if str(k).lower() in state_keys:
                            state = _stringify(v)
                            if state is not None:
                                found.append(state)
                        else:
                            found.extend(_search(v))

                elif isinstance(obj, list):
                    for item in obj:
                        found.extend(_search(item))

                return found

            states = _search(entry)
            return states[0] if states else None

        def _get_identifier(entry):
            lower_entry = {str(k).lower(): v for k, v in entry.items()}

            for key in (
                "interface",
                "if_name",
                "ifname",
                "neighbor",
                "system_id",
                "sys_id",
                "neighbor_system_id",
                "instance",
            ):
                if key in lower_entry:
                    value = _stringify(lower_entry[key])
                    if value:
                        return value

            return "unknown"

        def _is_up(state):
            return state is not None and state.lower() in (
                "up",
                "established",
                "adjacent",
                "full",
            )

        def _extract_raw_states(raw):
            states = []

            for line in str(raw).splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue

                for part in parts:
                    cleaned = part.strip(".,;:()[]{}").lower()
                    if cleaned in (
                        "up",
                        "down",
                        "init",
                        "2-way",
                        "adjacent",
                        "established",
                        "full",
                    ):
                        states.append(part.strip(".,;:()[]{}"))
                        break

            return states

        failures = []
        neighbor_devices = 0

        for device in devices:
            try:
                device.connect(via="cli")
                raw = device.execute("show isis neighbors")
            except Exception as exc:
                self.log.warning("Skipping device %s: %s", device.name, exc)
                continue

            try:
                parsed = device.parse("show isis neighbors")
            except Exception as exc:
                self.log.warning("Parse failed for device %s: %s", device.name, exc)
                parsed = None

            raw_text = str(raw)
            raw_lower = raw_text.lower()

            skip_markers = (
                "not recognized",
                "invalid input",
                "command not found",
                "not running",
                "not configured",
                "no isis",
                "isis is not running",
            )

            if any(marker in raw_lower for marker in skip_markers):
                continue

            entries = _find_neighbor_entries(parsed) if parsed else []

            if entries:
                neighbor_devices += 1

                for entry in entries:
                    state = _get_state(entry)
                    identifier = _get_identifier(entry)

                    if state is None:
                        failures.append(
                            f"{device.name}: neighbor {identifier} state missing"
                        )
                    elif not _is_up(state):
                        failures.append(
                            f"{device.name}: neighbor {identifier} state is {state}"
                        )

                continue

            raw_states = _extract_raw_states(raw_text)

            if raw_states:
                neighbor_devices += 1

                for state in raw_states:
                    if not _is_up(state):
                        failures.append(f"{device.name}: neighbor state is {state}")

                continue

            if "system id" in raw_lower or "state" in raw_lower:
                failures.append(
                    f"{device.name}: ISIS is running but no neighbors are up"
                )

        if failures:
            self.failed("ISIS neighbor verification failed: " + "; ".join(failures))
            return

        if neighbor_devices == 0:
            self.failed("No ISIS neighbors found on any device in the testbed")
            return

        self.log.info("All discovered ISIS neighbors are up")

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass

if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)