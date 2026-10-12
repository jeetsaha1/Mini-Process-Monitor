
import unittest

from process_monitor.actions import (
    search_processes,
    sort_processes,
)


class TestProcessActions(unittest.TestCase):

    def setUp(self):
        self.processes = [
            {
                "pid": 10,
                "name": "browser",
                "cpu_percent": 20.0,
                "memory_mb": 300.0,
            },
            {
                "pid": 20,
                "name": "editor",
                "cpu_percent": 5.0,
                "memory_mb": 100.0,
            },
            {
                "pid": 30,
                "name": "terminal",
                "cpu_percent": None,
                "memory_mb": None,
            },
        ]

    def test_search_by_name(self):
        result = search_processes(self.processes, "BROWSER")
        self.assertEqual([p["pid"] for p in result], [10])

    def test_search_by_pid(self):
        result = search_processes(self.processes, "20")
        self.assertEqual([p["pid"] for p in result], [20])

    def test_search_empty_query(self):
        result = search_processes(self.processes, "")
        self.assertEqual(len(result), 3)

    def test_sort_cpu(self):
        result = sort_processes(self.processes, "cpu")
        self.assertEqual([p["pid"] for p in result], [10, 20, 30])

    def test_sort_memory(self):
        result = sort_processes(self.processes, "memory")
        self.assertEqual([p["pid"] for p in result], [10, 20, 30])

    def test_sort_pid(self):
        result = sort_processes(self.processes, "pid")
        self.assertEqual([p["pid"] for p in result], [10, 20, 30])

    def test_sort_name(self):
        result = sort_processes(self.processes, "name")
        self.assertEqual(
            [p["name"] for p in result],
            ["browser", "editor", "terminal"],
        )

    def test_invalid_sort(self):
        with self.assertRaises(ValueError):
            sort_processes(self.processes, "invalid")


if __name__ == "__main__":
    unittest.main()
