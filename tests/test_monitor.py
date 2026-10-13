import unittest
from unittest.mock import MagicMock, patch

import psutil

from process_monitor.monitor import (
    get_process_list,
    get_memory_stats,
    format_memory,
)


class TestGetProcessList(unittest.TestCase):

    @patch("process_monitor.monitor.psutil.process_iter")
    def test_returns_normalized_process_records(self, mock_process_iter):
        process = MagicMock()
        process.info = {
            "pid": 1234,
            "name": "example",
            "status": "sleeping",
            "num_threads": 2,
        }

        # Mock process memory usage: 50 MB RSS
        process.memory_info.return_value.rss = 50 * 1024 * 1024
        process.memory_percent.return_value = 0.5

        mock_process_iter.return_value = [process]

        records = get_process_list()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pid"], 1234)
        self.assertEqual(records[0]["name"], "example")
        self.assertEqual(records[0]["status"], "sleeping")
        self.assertEqual(records[0]["thread_count"], 2)
        self.assertIsNone(records[0]["cpu_percent"])
        self.assertEqual(records[0]["memory_mb"], 50.0)
        self.assertEqual(records[0]["memory_percent"], 0.5)

    @patch("process_monitor.monitor.psutil.process_iter")
    def test_returns_empty_list_when_no_processes(self, mock_process_iter):
        mock_process_iter.return_value = []

        self.assertEqual(get_process_list(), [])

    @patch("process_monitor.monitor.psutil.process_iter")
    def test_skips_process_that_disappears(self, mock_process_iter):
        disappearing_process = MagicMock()
        disappearing_process.info = psutil.NoSuchProcess(1234)

        valid_process = MagicMock()
        valid_process.info = {
            "pid": 5678,
            "name": "valid-process",
            "status": "sleeping",
            "num_threads": 1,
        }

        mock_process_iter.return_value = [
            disappearing_process,
            valid_process,
        ]

        # Simulate NoSuchProcess when reading the first process's info.
        type(disappearing_process).info = property(
            lambda self: (_ for _ in ()).throw(psutil.NoSuchProcess(1234))
        )

        records = get_process_list()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pid"], 5678)

    @patch("process_monitor.monitor.psutil.process_iter")
    def test_skips_process_when_access_is_denied(self, mock_process_iter):
        class DeniedProcess:
            @property
            def info(self):
                raise psutil.AccessDenied(pid=1234)

        valid_process = MagicMock()
        valid_process.info = {
            "pid": 5678,
            "name": "valid-process",
            "status": "sleeping",
            "num_threads": 1,
        }

        mock_process_iter.return_value = [DeniedProcess(), valid_process]

        records = get_process_list()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pid"], 5678)


if __name__ == "__main__":
    unittest.main()




from unittest.mock import patch


class TestGetCPUStats(unittest.TestCase):

    def setUp(self):
        import process_monitor.monitor as monitor
        monitor._cpu_sampling_started = False

    @patch("process_monitor.monitor.psutil.cpu_count", return_value=16)
    @patch("process_monitor.monitor.psutil.cpu_percent", return_value=25.5)
    def test_first_call_returns_sampling_status(self, mock_cpu, mock_cores):
        from process_monitor.monitor import get_cpu_stats

        result = get_cpu_stats()

        self.assertEqual(result["status"], "sampling")
        self.assertIsNone(result["total_percent"])
        self.assertEqual(result["cores"], 16)

    @patch("process_monitor.monitor.psutil.cpu_count", return_value=16)
    @patch("process_monitor.monitor.psutil.cpu_percent", return_value=25.5)
    def test_later_call_returns_cpu_percentage(self, mock_cpu, mock_cores):
        import process_monitor.monitor as monitor
        monitor._cpu_sampling_started = True

        result = monitor.get_cpu_stats()

        self.assertEqual(result["status"], "active")
        self.assertEqual(result["total_percent"], 25.5)
        self.assertEqual(result["cores"], 16)


class TestGetMemoryStats(unittest.TestCase):

    @patch("process_monitor.monitor.psutil.virtual_memory")
    def test_returns_system_memory_statistics(self, mock_memory):
        mock_memory.return_value.total = 8 * 1024**3
        mock_memory.return_value.used = 4 * 1024**3
        mock_memory.return_value.available = 4 * 1024**3
        mock_memory.return_value.percent = 50.0

        result = get_memory_stats()

        self.assertEqual(result["total_mb"], 8192.0)
        self.assertEqual(result["used_mb"], 4096.0)
        self.assertEqual(result["available_mb"], 4096.0)
        self.assertEqual(result["percent"], 50.0)
        self.assertEqual(result["status"], "active")

    @patch(
        "process_monitor.monitor.psutil.virtual_memory",
        side_effect=psutil.Error("Memory unavailable"),
    )
    def test_handles_memory_error(self, mock_memory):
        result = get_memory_stats()

        self.assertIsNone(result["total_mb"])
        self.assertIsNone(result["used_mb"])
        self.assertIsNone(result["available_mb"])
        self.assertIsNone(result["percent"])
        self.assertEqual(result["status"], "unavailable")


class TestFormatMemory(unittest.TestCase):

    def test_formats_bytes(self):
        self.assertEqual(format_memory(512), "512.00 B")

    def test_formats_kilobytes(self):
        self.assertEqual(format_memory(1024), "1.00 KB")

    def test_formats_megabytes(self):
        self.assertEqual(format_memory(1024**2), "1.00 MB")

    def test_formats_gigabytes(self):
        self.assertEqual(format_memory(1024**3), "1.00 GB")

    def test_handles_none(self):
        self.assertEqual(format_memory(None), "N/A")