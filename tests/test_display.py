"""Unit tests for Member 5: Terminal UI and Refresh Module.

These tests are narrowly scoped to Member 5's display and formatting deliverables.
They use controlled synthetic fixtures and do not depend on external systems,
live processes, or modules owned by other members (Members 1, 2, 3, 4, 6, 7, 8).
"""

import io
from unittest import TestCase, mock
import unittest

from process_monitor.display import (
    MISSING_VALUE_MARKER,
    SAMPLING_MARKER,
    clear_screen,
    confirm_action,
    display_process_table,
    display_system_summary,
    format_action_result,
    format_cpu_percent,
    format_memory_mb,
    format_memory_percent,
    format_menu,
    format_message,
    format_pid,
    format_process_details,
    format_process_table,
    format_status,
    format_system_summary,
    format_thread_count,
    prompt_input,
    prompt_menu_choice,
    refresh_view,
    render_dashboard,
    run_refresh_loop,
    truncate_text,
)


class TestDisplayFormattingHelpers(TestCase):
    """Test pure formatting helper functions."""

    def test_truncate_text(self):
        self.assertEqual(truncate_text("short", 10), "short")
        self.assertEqual(truncate_text("exact_10ch", 10), "exact_10ch")
        self.assertEqual(truncate_text("this_is_a_very_long_string", 12), "this_is_a...")
        self.assertEqual(truncate_text(None, 10), MISSING_VALUE_MARKER)

    def test_format_pid(self):
        self.assertEqual(format_pid(1234), "1234")
        self.assertEqual(format_pid(None), MISSING_VALUE_MARKER)
        self.assertEqual(format_pid("5678"), "5678")

    def test_format_cpu_percent(self):
        self.assertEqual(format_cpu_percent(15.2), "15.2%")
        self.assertEqual(format_cpu_percent(0.0), "0.0%")
        self.assertEqual(format_cpu_percent(None), MISSING_VALUE_MARKER)
        # Verify CPU sampling preservation
        self.assertEqual(format_cpu_percent("Sampling..."), SAMPLING_MARKER)
        self.assertEqual(format_cpu_percent("warmup"), SAMPLING_MARKER)

    def test_format_memory_mb(self):
        self.assertEqual(format_memory_mb(256.4), "256.4")
        self.assertEqual(format_memory_mb(None), MISSING_VALUE_MARKER)

    def test_format_memory_percent(self):
        self.assertEqual(format_memory_percent(3.5), "3.5%")
        self.assertEqual(format_memory_percent(None), MISSING_VALUE_MARKER)

    def test_format_thread_count(self):
        self.assertEqual(format_thread_count(8), "8")
        self.assertEqual(format_thread_count(None), MISSING_VALUE_MARKER)

    def test_format_status(self):
        self.assertEqual(format_status("running"), "running")
        self.assertEqual(format_status(None), MISSING_VALUE_MARKER)
        self.assertEqual(format_status(""), MISSING_VALUE_MARKER)


class TestProcessTableRendering(TestCase):
    """Test terminal process table rendering with various input states."""

    def setUp(self):
        self.sample_processes = [
            {
                "pid": 1001,
                "name": "system_service",
                "status": "running",
                "cpu_percent": 12.5,
                "memory_mb": 150.0,
                "memory_percent": 1.5,
                "thread_count": 8,
            },
            {
                "pid": 2002,
                "name": "worker_daemon",
                "status": "sleeping",
                "cpu_percent": 0.5,
                "memory_mb": 45.2,
                "memory_percent": 0.4,
                "thread_count": 2,
            },
        ]

    def test_process_table_rendering_all_fields(self):
        output = format_process_table(self.sample_processes)

        # Check title and headers
        self.assertIn("PROCESS TABLE", output)
        self.assertIn("PID", output)
        self.assertIn("Name", output)
        self.assertIn("Status", output)
        self.assertIn("CPU %", output)
        self.assertIn("Mem (MB)", output)
        self.assertIn("Mem %", output)
        self.assertIn("Threads", output)

        # Check row content
        self.assertIn("1001", output)
        self.assertIn("system_service", output)
        self.assertIn("12.5%", output)
        self.assertIn("150.0", output)
        self.assertIn("1.5%", output)
        self.assertIn("8", output)

        self.assertIn("2002", output)
        self.assertIn("worker_daemon", output)

    def test_process_table_missing_values(self):
        """Verify None values are rendered as N/A and not misrepresented as 0 or empty."""
        sparse_proc = [
            {
                "pid": None,
                "name": None,
                "status": None,
                "cpu_percent": None,
                "memory_mb": None,
                "memory_percent": None,
                "thread_count": None,
            }
        ]
        output = format_process_table(sparse_proc)
        self.assertIn("N/A", output)
        # Must not fabricate zeros
        self.assertNotIn("0.0%", output)

    def test_process_table_cpu_sampling_state(self):
        """Verify sampling state preserves 'Sampling...' indicator."""
        sampling_proc = [
            {
                "pid": 3003,
                "name": "warming_process",
                "status": "running",
                "cpu_percent": "Sampling...",
                "memory_mb": 50.0,
                "memory_percent": 0.5,
                "thread_count": 1,
            }
        ]
        output = format_process_table(sampling_proc)
        self.assertIn("Sampling...", output)

    def test_process_table_empty_list(self):
        """Verify empty process list renders a clean message without throwing."""
        output = format_process_table([])
        self.assertIn("No processes to display", output)

    def test_process_table_sort_by_indicator(self):
        """Verify sort_by column label appears in table title."""
        output = format_process_table(self.sample_processes, sort_by="cpu_percent")
        self.assertIn("[Sorted by: cpu_percent]", output)

    def test_process_table_does_not_mutate_input(self):
        """Ensure input dictionaries remain unaltered."""
        original_copy = [dict(p) for p in self.sample_processes]
        format_process_table(self.sample_processes)
        self.assertEqual(self.sample_processes, original_copy)

    def test_display_process_table_stdout(self):
        """Verify display_process_table prints to standard output."""
        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            display_process_table(self.sample_processes)
            self.assertIn("PROCESS TABLE", fake_out.getvalue())


class TestSystemSummaryPresentation(TestCase):
    """Test system summary presentation formatting."""

    def test_system_summary_valid_data(self):
        cpu_stats = {"total_percent": 24.5, "cores": 8}
        memory_stats = {
            "total_mb": 16384.0,
            "used_mb": 8192.0,
            "available_mb": 8192.0,
            "percent": 50.0,
        }
        output = format_system_summary(cpu_stats, memory_stats)

        self.assertIn("SYSTEM SUMMARY", output)
        self.assertIn("24.5%", output)
        self.assertIn("8 logical cores", output)
        self.assertIn("8,192.0 MB / 16,384.0 MB", output)
        self.assertIn("50.0%", output)

    def test_system_summary_sampling_cpu(self):
        cpu_stats = {"status": "sampling"}
        memory_stats = {"used_mb": 2048.0, "total_mb": 4096.0, "percent": 50.0}
        output = format_system_summary(cpu_stats, memory_stats)

        self.assertIn(SAMPLING_MARKER, output)

    def test_system_summary_none_inputs(self):
        output = format_system_summary(None, None)
        self.assertIn("CPU Usage:    N/A", output)
        self.assertIn("Memory Usage: N/A", output)

    def test_display_system_summary_stdout(self):
        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            display_system_summary()
            self.assertIn("SYSTEM SUMMARY", fake_out.getvalue())


class TestMenuAndDetailsView(TestCase):
    """Test menu formatting, choices, and details display."""

    def test_format_menu(self):
        menu = format_menu()
        self.assertIn("[1] Refresh Process Table", menu)
        self.assertIn("[2] Search Processes", menu)
        self.assertIn("[3] Sort Process Table", menu)
        self.assertIn("[4] View Process Details", menu)
        self.assertIn("[5] Terminate Process", menu)
        self.assertIn("[6] Live Auto-Refresh Mode", menu)
        self.assertIn("[7] Exit Mini Process Monitor", menu)

    def test_format_menu_with_active_sort(self):
        menu = format_menu(current_sort="memory_mb")
        self.assertIn("(Active: memory_mb)", menu)

    def test_prompt_menu_choice(self):
        with mock.patch("builtins.input", return_value="1"):
            choice = prompt_menu_choice()
            self.assertEqual(choice, "1")

        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            choice = prompt_menu_choice()
            self.assertEqual(choice, "7")

    def test_prompt_input(self):
        with mock.patch("builtins.input", return_value="my_app"):
            val = prompt_input("Search: ")
            self.assertEqual(val, "my_app")

        with mock.patch("builtins.input", return_value=""):
            val = prompt_input("Sort: ", default="cpu_percent")
            self.assertEqual(val, "cpu_percent")

        with mock.patch("builtins.input", side_effect=KeyboardInterrupt):
            val = prompt_input("Query: ")
            self.assertIsNone(val)

    def test_confirm_action(self):
        with mock.patch("builtins.input", return_value="y"):
            self.assertTrue(confirm_action("Terminate PID 123?"))

        with mock.patch("builtins.input", return_value="yes"):
            self.assertTrue(confirm_action("Terminate PID 123?"))

        with mock.patch("builtins.input", return_value="n"):
            self.assertFalse(confirm_action("Terminate PID 123?"))

        with mock.patch("builtins.input", return_value=""):
            self.assertFalse(confirm_action("Terminate PID 123?", default=False))

    def test_format_process_details_valid(self):
        details = {
            "pid": 5555,
            "name": "python.exe",
            "status": "running",
            "cpu_percent": 3.2,
            "memory_mb": 95.0,
            "memory_percent": 1.1,
            "thread_count": 5,
            "ppid": 1000,
            "username": "os_student",
        }
        output = format_process_details(details)
        self.assertIn("PROCESS DETAILS: PID 5555", output)
        self.assertIn("python.exe", output)
        self.assertIn("3.2%", output)
        self.assertIn("os_student", output)

    def test_format_process_details_error(self):
        details = {"error": "NoSuchProcess: process terminated before inspection"}
        output = format_process_details(details)
        self.assertIn("[ERROR]", output)
        self.assertIn("NoSuchProcess", output)


class TestMessagesAndActionResults(TestCase):
    """Test status messages and action outcome presentation."""

    def test_format_message(self):
        self.assertEqual(format_message("System ready", "info"), "[INFO] System ready")
        self.assertEqual(format_message("Action failed", "error"), "[ERROR] Action failed")
        self.assertEqual(format_message("Updated", "success"), "[SUCCESS] Updated")

    def test_format_action_result_dict(self):
        success_res = {"success": True, "message": "Signal sent", "pid": 4321}
        out_success = format_action_result(success_res)
        self.assertIn("[SUCCESS]", out_success)
        self.assertIn("PID 4321", out_success)
        self.assertIn("Signal sent", out_success)

        fail_res = {"success": False, "message": "Permission denied", "error": "AccessDenied", "pid": 1}
        out_fail = format_action_result(fail_res)
        self.assertIn("[ERROR]", out_fail)
        self.assertIn("AccessDenied", out_fail)


class TestDashboardAndRefreshCoordination(TestCase):
    """Test dashboard rendering and refresh loop coordination."""

    def test_render_dashboard(self):
        procs = [{"pid": 100, "name": "app", "status": "running", "cpu_percent": 1.0, "memory_mb": 10.0, "memory_percent": 0.1, "thread_count": 1}]
        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            render_dashboard(
                processes=procs,
                cpu_stats={"total_percent": 5.0},
                memory_stats={"used_mb": 500.0, "total_mb": 1000.0, "percent": 50.0},
                message="[INFO] Test message",
                clear=False
            )
            output = fake_out.getvalue()
            self.assertIn("MINI PROCESS MONITOR", output)
            self.assertIn("SYSTEM SUMMARY", output)
            self.assertIn("[INFO] Test message", output)
            self.assertIn("PROCESS TABLE", output)

    def test_refresh_view_callback(self):
        procs = [{"pid": 101, "name": "service", "status": "running", "cpu_percent": 2.0, "memory_mb": 20.0, "memory_percent": 0.2, "thread_count": 2}]
        mock_callback = mock.MagicMock(return_value=(procs, {"total_percent": 10.0}, {"used_mb": 100.0}, "pid", None))

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            refresh_view(mock_callback, clear=False)
            self.assertTrue(mock_callback.called)
            self.assertIn("service", fake_out.getvalue())

    def test_run_refresh_loop_max_iterations(self):
        """Verify refresh loop terminates cleanly after max_iterations without hanging."""
        counter = {"calls": 0}

        def mock_fetch():
            counter["calls"] += 1
            return ([], None, None, None, None)

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out, mock.patch("time.sleep", return_value=None):
            run_refresh_loop(mock_fetch, interval=0.1, max_iterations=2)
            self.assertEqual(counter["calls"], 2)
            self.assertIn("Clean exit from refresh mode", fake_out.getvalue())

    def test_run_refresh_loop_keyboard_interrupt(self):
        """Verify KeyboardInterrupt is handled gracefully without unhandled exception."""
        def mock_fetch_interrupt():
            raise KeyboardInterrupt()

        with mock.patch("sys.stdout", new=io.StringIO()) as fake_out, mock.patch("time.sleep", return_value=None):
            run_refresh_loop(mock_fetch_interrupt, interval=0.1, max_iterations=5)
            self.assertIn("Live refresh stopped by user (Ctrl+C)", fake_out.getvalue())

    def test_clear_screen_non_tty_safe(self):
        """Ensure clear_screen does not issue os.system on non-TTY streams."""
        with mock.patch("sys.stdout.isatty", return_value=False), mock.patch("os.system") as mock_os_system:
            clear_screen()
            mock_os_system.assert_not_called()

    def test_standalone_ui_test_harness_exit(self):
        """Verify the standalone UI test harness runs and exits cleanly on option 7."""
        from process_monitor.display import _run_standalone_ui_test
        with mock.patch("builtins.input", return_value="7"), mock.patch("sys.stdout", new=io.StringIO()) as fake_out:
            _run_standalone_ui_test()
            self.assertIn("MEMBER 5 UI TEST HARNESS", fake_out.getvalue())
            self.assertIn("Exiting standalone UI test harness", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()

