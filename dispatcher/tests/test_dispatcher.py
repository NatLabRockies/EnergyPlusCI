import os
import unittest
from unittest import mock

os.environ.setdefault("PROXMOX_URL", "https://proxmox.invalid/api2/json")
os.environ.setdefault("PROXMOX_NODE", "proxmox")
os.environ.setdefault("PROXMOX_TOKEN_ID", "test@pam!dispatcher")
os.environ.setdefault("PROXMOX_TOKEN_SECRET", "test-secret")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

from dispatcher import dispatcher


class DispatcherTests(unittest.TestCase):
    def test_queued_jobs_include_in_progress_workflows(self):
        runs_by_status = {
            "queued": [{"id": 10}],
            "in_progress": [{"id": 20}, {"id": 30}],
        }
        jobs_by_run = {
            10: [{"id": 100, "status": "queued"}],
            20: [{"id": 200, "status": "queued"}],
            30: [{"id": 100, "status": "queued"}],
        }

        with (
            mock.patch.object(
                dispatcher,
                "list_workflow_runs",
                side_effect=lambda status: runs_by_status[status],
            ) as list_runs,
            mock.patch.object(
                dispatcher,
                "list_jobs_for_run",
                side_effect=lambda run_id: jobs_by_run[run_id],
            ),
        ):
            jobs = dispatcher.list_queued_jobs()

        self.assertEqual([100, 200], [job["id"] for job in jobs])
        self.assertEqual(
            [mock.call("queued"), mock.call("in_progress")],
            list_runs.call_args_list,
        )

    def test_unregistered_vm_is_active_during_boot_grace(self):
        vm = {
            "name": "energyplus-2404-runner-200",
            "status": "running",
            "uptime": 599,
        }

        self.assertTrue(dispatcher.runner_vm_is_active(vm, {}, boot_timeout=600))

    def test_unregistered_vm_is_inactive_after_boot_grace(self):
        vm = {
            "name": "energyplus-2404-runner-200",
            "status": "running",
            "uptime": 600,
        }

        self.assertFalse(dispatcher.runner_vm_is_active(vm, {}, boot_timeout=600))

    def test_online_github_runner_remains_active_after_boot_grace(self):
        name = "energyplus-2404-runner-200"
        vm = {"name": name, "status": "running", "uptime": 3600}
        github_runners = {name: {"name": name, "status": "online"}}

        self.assertTrue(
            dispatcher.runner_vm_is_active(vm, github_runners, boot_timeout=600)
        )

    def test_cleanup_recycles_unregistered_vm_after_boot_grace(self):
        vm = {
            "name": "energyplus-2404-runner-200",
            "vmid": 200,
            "status": "running",
            "uptime": dispatcher.RUNNER_BOOT_TIMEOUT,
        }
        pools = [
            {
                "node": "proxmox",
                "runner_name_prefix": "energyplus-2404-runner",
            }
        ]

        with (
            mock.patch.object(dispatcher, "delete_vm") as delete_vm,
            mock.patch.object(dispatcher, "delete_snippet") as delete_snippet,
        ):
            deleted = dispatcher.cleanup_unready_runners(pools, {"proxmox": [vm]}, {})

        self.assertTrue(deleted)
        delete_vm.assert_called_once_with("proxmox", 200)
        delete_snippet.assert_called_once_with("energyplus-2404-runner-200.yaml")

    def test_ccache_mount_is_bounded_and_optional(self):
        pool = {
            "ccache_mount": {
                "source": "cache.example:/srv/ccache",
                "mount_point": "/mnt/ccache path",
                "type": "nfs4",
                "options": "rw,hard",
                "timeout_seconds": 23,
                "directories": ["ubuntu-24.04"],
            }
        }

        command = dispatcher.render_ccache_setup_commands(pool)

        self.assertIn("/usr/bin/timeout", command)
        self.assertIn("23s", command)
        self.assertIn("continuing without it", command)
        self.assertIn("'/mnt/ccache path'", command)

    def test_ccache_setup_is_noop_without_source(self):
        self.assertEqual(
            '  - ["/bin/true"]',
            dispatcher.render_ccache_setup_commands({"ccache_mount": {}}),
        )


if __name__ == "__main__":
    unittest.main()
