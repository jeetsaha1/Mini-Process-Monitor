import sys 
import os 
sys.path.insert(0,
 os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
import unittest
from unittest.mock import MagicMock, patch
import psutil
from process_monitor.actions import terminate_process

class TestSafeTermination(unittest.TestCase):
    def test_self_protection(self):
        my_pid = os.getpid()
        result = terminate_process(my_pid)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["error_type"], "SelfProtection")
        self.assertIn("Self-protection trigger", result["message"])

    @patch("psutil.Process")
    def test_access_denied(self, mock_process_class):
        mock_process_class.side_effect = psutil.AccessDenied()
        result = terminate_process(99999)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "AccessDenied")
        self.assertIn("Access denied", result["message"])

    @patch("psutil.Process")
    def test_no_such_process(self, mock_process_class):
        mock_process_class.side_effect = psutil.NoSuchProcess(pid=99999)
        result = terminate_process(99999)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "NoSuchProcess")
        self.assertIn("no longer exists", result["message"])

    @patch("psutil.Process")
    def test_successful_graceful_termination(self, mock_process_class):
        mock_proc_instance = MagicMock()
        mock_proc_instance.name.return_value = "dummy_app.exe"
        mock_process_class.return_value = mock_proc_instance
        result = terminate_process(1234, force=False)
        mock_proc_instance.terminate.assert_called_once()
        mock_proc_instance.wait.assert_called_once_with(timeout=3)
        self.assertEqual(result["status"], "success")
        self.assertIn("Successfully terminated", result["message"])

if __name__ == "__main__":
    unittest.main()
