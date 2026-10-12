"""Agendamento Docker usa relógio e arquivos sintéticos, sem executar backups reais."""

import importlib.util
import json
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

path = Path(__file__).resolve().parents[2] / "deploy/docker/backup_scheduler.py"
spec = importlib.util.spec_from_file_location("docker_backup_scheduler", path)
scheduler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scheduler)


class DockerBackupScheduleTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
        self.zone = ZoneInfo("America/Sao_Paulo")
        self.runner = Mock(return_value=0)
        self.schedule = scheduler.Schedule(self.runner, now=lambda: self.now, zone=self.zone)

    def test_startup_runs_immediately_and_then_waits_for_three_am_local(self):
        self.assertTrue(self.schedule.tick())
        self.runner.assert_called_once_with()
        self.assertEqual(self.schedule.next_run, datetime(2026, 10, 7, 6, tzinfo=timezone.utc))
        self.assertFalse(self.schedule.tick())

    def test_three_attempts_then_hourly_recovery_never_loops_without_waiting(self):
        self.runner.return_value = 1
        for expected_delay in (timedelta(minutes=5), timedelta(minutes=5), timedelta(hours=1)):
            self.assertTrue(self.schedule.tick())
            self.assertEqual(self.schedule.next_run, self.now + expected_delay)
            self.assertFalse(self.schedule.tick())
            self.now = self.schedule.next_run
        self.assertEqual(self.runner.call_count, 3)
        self.runner.return_value = 0
        self.assertTrue(self.schedule.tick())
        self.assertEqual(self.schedule.attempts, 0)
        self.assertEqual(self.schedule.next_run, scheduler.next_daily_run(self.now, self.zone))

    def test_many_days_offline_recover_and_restore_the_daily_schedule(self):
        self.runner.return_value = 1
        for _day in range(7):
            self.assertTrue(self.schedule.tick())
            self.now += timedelta(days=1)
        self.runner.return_value = 0
        self.assertTrue(self.schedule.tick())
        self.assertEqual(self.schedule.next_run, datetime(2026, 10, 14, 6, tzinfo=timezone.utc))

    def test_next_run_accounts_for_calendar_boundaries_and_local_offsets(self):
        cases = (
            (datetime(2026, 12, 31, 23, tzinfo=timezone.utc), "America/Sao_Paulo", 6),
            (datetime(2026, 12, 31, 23, tzinfo=timezone.utc), "UTC", 3),
        )
        for now, zone_name, utc_hour in cases:
            with self.subTest(zone=zone_name):
                result = scheduler.next_daily_run(now, ZoneInfo(zone_name))
                self.assertEqual(result, datetime(2027, 1, 1, utc_hour, tzinfo=timezone.utc))
        before = datetime(2026, 10, 6, 5, 59, tzinfo=timezone.utc)
        self.assertEqual(
            scheduler.next_daily_run(before, self.zone),
            datetime(2026, 10, 6, 6, tzinfo=timezone.utc),
        )
        self.assertEqual(
            scheduler.next_daily_run(before + timedelta(minutes=1), self.zone),
            datetime(2026, 10, 7, 6, tzinfo=timezone.utc),
        )

    def test_backup_duration_does_not_schedule_an_already_passed_deadline(self):
        self.now = datetime(2026, 10, 6, 5, 59, tzinfo=timezone.utc)
        self.schedule.next_run = self.now

        def finish_after_three_am():
            self.now += timedelta(minutes=3)
            return 0

        self.runner.side_effect = finish_after_three_am
        self.schedule.tick()
        self.assertEqual(self.schedule.next_run, datetime(2026, 10, 7, 6, tzinfo=timezone.utc))

    def test_process_launch_failure_uses_normal_retry_and_stopped_loop_does_no_work(self):
        self.runner.side_effect = OSError("synthetic failure")
        self.assertTrue(self.schedule.tick())
        self.assertEqual(self.schedule.next_run, self.now + timedelta(minutes=5))
        stopped = Event()
        stopped.set()
        self.schedule.run(stopped)
        self.assertEqual(self.runner.call_count, 1)

    def test_single_scheduler_lock_is_exclusive_and_released_after_failure(self):
        with TemporaryDirectory() as directory:
            lock = Path(directory) / "scheduler.lock"
            with scheduler.scheduler_lock(lock):
                with self.assertRaisesRegex(RuntimeError, "Outro agendador"):
                    with scheduler.scheduler_lock(lock):
                        self.fail("A segunda réplica não deve obter o lock.")
            with self.assertRaises(ValueError):
                with scheduler.scheduler_lock(lock):
                    raise ValueError("synthetic failure")
            with scheduler.scheduler_lock(lock):
                pass

    def test_job_passes_paths_as_arguments_and_forwards_stop_to_child(self):
        process = Mock()
        process.__enter__ = Mock(return_value=process)
        process.__exit__ = Mock(return_value=False)
        process.wait.return_value = 0
        stopped = Event()
        with patch.object(scheduler.subprocess, "Popen", return_value=process) as launch:
            self.assertEqual(
                scheduler.run_job(Path("state with spaces"), "external path", stopped), 0
            )
            command = launch.call_args.args[0]
            self.assertEqual(
                command[-4:],
                ["--state-dir", "state with spaces", "--external-directory", "external path"],
            )
            process.terminate.assert_not_called()
            stopped.set()
            self.assertEqual(scheduler.run_job(Path("state"), None, stopped), 1)
            process.terminate.assert_called_once()

    def test_unresponsive_child_is_killed_after_timeout(self):
        process = Mock()
        process.__enter__ = Mock(return_value=process)
        process.__exit__ = Mock(return_value=False)
        process.wait.side_effect = [subprocess.TimeoutExpired("test", 1), None]
        stopped = Event()
        stopped.set()
        with patch.object(scheduler.subprocess, "Popen", return_value=process):
            self.assertEqual(scheduler.run_job(Path("state"), None, stopped), 1)
        process.kill.assert_called_once()


class DockerBackupHealthTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "logs").mkdir()
        (self.root / "backups").mkdir()
        self.now = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
        self.status = self.root / "logs/backup-status.json"
        self.write_status(self.now, True)
        self.write_backup(self.now)

    def write_status(self, checked_at, success):
        self.status.write_text(
            json.dumps({"checked_at": checked_at.isoformat(), "success": success}),
            encoding="utf-8",
        )

    def write_backup(self, created):
        filename = f"scheduled-{created.strftime('%Y%m%dT%H%M%S%fZ')}-{'a' * 32}.fhbackup"
        backup = self.root / "backups" / filename
        backup.write_text("synthetic envelope", encoding="ascii")
        return backup

    def test_health_accepts_a_recent_success_and_local_backup_without_opening_database(self):
        scheduler.check_health(self.root, now=self.now + timedelta(hours=25))

    def test_health_fails_for_failure_missing_backup_stale_and_future_dates(self):
        self.write_status(self.now, False)
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now)
        self.write_status(self.now, True)
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now + timedelta(hours=27))
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now - timedelta(minutes=1))
        for path in (self.root / "backups").iterdir():
            path.unlink()
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now)

    def test_success_status_does_not_hide_stale_backup_or_naive_date(self):
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now + timedelta(hours=27))
        self.write_status(self.now + timedelta(hours=27), True)
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now + timedelta(hours=27))
        self.write_status(self.now.replace(tzinfo=None), True)
        with self.assertRaises(ValueError):
            scheduler.check_health(self.root, now=self.now)

    def test_malformed_status_and_excessive_file_are_rejected(self):
        self.status.write_text("[]", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now)
        self.status.write_text("x" * 4097, encoding="utf-8")
        with self.assertRaises(RuntimeError):
            scheduler.check_health(self.root, now=self.now)
        with self.assertRaises(ValueError):
            scheduler.check_health(self.root, now=self.now, max_age_hours=0)


if __name__ == "__main__":
    unittest.main()
