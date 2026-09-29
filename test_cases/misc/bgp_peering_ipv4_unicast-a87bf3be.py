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


class VerifyBgpIpv4UnicastEstablished(aetest.Testcase):
    @aetest.test
    def capture_pre_change_state(self):
        self._capture_bgp_state(phase="pre")

    @aetest.test
    def perform_maintenance_action(self):
        logger.info("Placeholder: maintenance action would occur here.")

    @aetest.test
    def capture_post_change_state(self):
        self._capture_bgp_state(phase="post")

    @aetest.test
    def final_result(self):
        self.passed(
            "BGP IPv4 unicast state captured pre and post maintenance; "
            "platform baseline comparison will evaluate drift."
        )

    def _capture_bgp_state(self, phase):
        testbed = self.parameters.get("testbed")
        if testbed is None:
            self.failed("No testbed available for this run")
            return

        devices = list(testbed.devices.values())
        if not devices:
            self.failed("No devices in testbed; cannot capture BGP state")
            return

        any_success = False

        for device in devices:
            device_name = getattr(device, "name", str(device))

            print(json.dumps({"netvalid_device_started": {"device": device_name}}))

            try:
                device.connect(via="cli")
                state = device.learn("bgp")

                if isinstance(state, dict):
                    parsed = state.get("info", state)
                else:
                    parsed = getattr(state, "info", {})

                if parsed is None:
                    parsed = {}

                print(
                    json.dumps(
                        {
                            "netvalid_baseline_state": {
                                "device": device_name,
                                "key": "bgp",
                                "parsed": parsed,
                                "phase": phase,
                                "exclude": [
                                    "connections_established",
                                    "connections_dropped",
                                    "last_reset",
                                ],
                            }
                        },
                        default=str,
                    )
                )

                established, detail = self._is_ipv4_unicast_established(parsed)
                status = "pass" if established else "fail"

                print(
                    json.dumps(
                        {
                            "netvalid_device_result": {
                                "device": device_name,
                                "status": status,
                                "detail": f"BGP IPv4 unicast state captured ({phase}); {detail}",
                            }
                        },
                        default=str,
                    )
                )

                any_success = True

            except Exception as exc:
                logger.warning("Failed to capture BGP state on %s: %s", device_name, exc)
                print(
                    json.dumps(
                        {
                            "netvalid_device_result": {
                                "device": device_name,
                                "status": "error",
                                "detail": f"Failed to capture BGP state ({phase}): {exc}",
                            }
                        },
                        default=str,
                    )
                )

        if not any_success:
            self.failed("No devices could be reached or BGP state could be captured")

    def _is_ipv4_unicast_established(self, parsed):
        found = False
        all_established = True

        def process_peers(peers):
            nonlocal found, all_established

            if not isinstance(peers, dict):
                return

            for peer_data in peers.values():
                if not isinstance(peer_data, dict):
                    continue

                found = True
                peer_state = str(
                    peer_data.get("state", peer_data.get("peer_state", ""))
                ).lower()

                if peer_state not in ("established", "up"):
                    all_established = False

        try:
            root = parsed.get("info", parsed) if isinstance(parsed, dict) else {}

            vrf_dict = root.get("vrf", {})
            if not isinstance(vrf_dict, dict) or not vrf_dict:
                if isinstance(root, dict) and "address_family" in root:
                    vrf_dict = {"default": root}
                else:
                    vrf_dict = {}

            for vrf_data in vrf_dict.values():
                if not isinstance(vrf_data, dict):
                    continue

                address_family = vrf_data.get("address_family", {})
                if not isinstance(address_family, dict):
                    continue

                for afi, afi_data in address_family.items():
                    if str(afi).lower() != "ipv4":
                        continue

                    if not isinstance(afi_data, dict):
                        continue

                    safi = afi_data.get("safi")

                    if safi and str(safi).lower() == "unicast":
                        process_peers(afi_data.get("peers"))
                    elif not safi:
                        process_peers(afi_data.get("peers"))

                    unicast = afi_data.get("unicast")
                    if isinstance(unicast, dict):
                        process_peers(unicast.get("peers"))

            if not found:
                return False, "No IPv4 unicast BGP peers found"

            if all_established:
                return True, "All IPv4 unicast BGP peers are established"

            return False, "One or more IPv4 unicast BGP peers are not established"

        except Exception as exc:
            return False, f"Unable to evaluate IPv4 unicast BGP state: {exc}"


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def cleanup(self):
        pass


if __name__ == "__main__":
    testbed_path = os.environ.get("TESTBED_PATH")
    testbed = loader.load(testbed_path) if testbed_path else None
    result = aetest.main(testbed=testbed)
    sys.exit(0 if result else 1)