# Member 5 Handoff: Terminal UI and Refresh Module

**Author:** Member 5  
**Component:** `process_monitor/display.py`  
**Target Project:** Mini Process Monitor (Operating Systems Group Project)  
**Status:** Implemented, Tested, Ready for Integration  

---

## 1. Document Review & Architectural Context

The complete 13-page project specification (`Mini_Process_Monitor_Complete_Project_Plan.docx`) was reviewed in detail prior to implementation, including:
- Layer responsibilities (Section 7.1)
- Proposed repository structure (Section 8)
- Module design & shared interfaces (Section 9)
- Standard process-record schema (Section 9.1)
- CPU sampling rules (Section 9.2)
- Safe termination design (Section 10)
- Ten-member work allocation (Section 11)
- Windows 11 and Linux portability requirements (Section 14 & 15)
- Appendix A Handoff Checklist

This implementation strictly implements **Member 5 deliverables only**. No code belonging to Members 1, 2, 3, 4, 6, 7, 8, 9, or 10 was implemented, replaced, or duplicated.

---

## 2. Deliverables & Files Created

| File | Purpose | Ownership |
|---|---|---|
| `process_monitor/display.py` | Primary Terminal UI and refresh display component | Member 5 |
| `process_monitor/__init__.py` | Package marker | Shared / Member 1 |
| `tests/test_display.py` | Focused unit tests for Member 5's display logic (32 tests) | Narrow component test |
| `MEMBER_5_HANDOFF.md` | Integration contract and handoff documentation | Member 5 |

---

## 3. Member 5 Responsibilities Implemented

1. **Terminal Process-Table Rendering:**
   - Public interface `display_process_table(processes, sort_by=None)`.
   - Clean column alignment with headers: `PID`, `Name`, `Status`, `CPU %`, `Mem (MB)`, `Mem %`, `Threads`.
   - Responsive column width adapting dynamically to terminal width (`shutil.get_terminal_size()`) with bounded truncation for process names.
   - Non-destructive display: processes records are never mutated.
   - Clear display of missing values as `"N/A"` (never fabricating zeroes).
   - Preservation of CPU sampling states (renders `"Sampling..."`).
   - Graceful handling of empty process lists.

2. **System Summary Presentation:**
   - Public interface `display_system_summary(cpu_stats=None, memory_stats=None)`.
   - Displays system-wide CPU usage (percentage, logical core count, sampling status).
   - Displays system memory usage (Used MB / Total MB, usage %, available MB).
   - Graceful fallback to `"N/A"` for missing or partially populated data.

3. **Menu Presentation and Navigation:**
   - Public interfaces `display_menu(current_sort=None)` and `prompt_menu_choice()`.
   - Beginner-friendly menu options:
     - `[1]` Refresh Process Table
     - `[2]` Search Processes (delegated to Member 6 via controller)
     - `[3]` Sort Process Table (delegated to Member 6 via controller)
     - `[4]` View Process Details (delegated to Member 6 via controller)
     - `[5]` Terminate Process (safe confirmed request delegated to Member 7 via controller)
     - `[6]` Live Auto-Refresh Mode (coordinated with controller)
     - `[7]` Exit
   - Safe input reading handling `KeyboardInterrupt` (Ctrl+C) and `EOFError`.

4. **Confirmation Flow:**
   - Public interface `confirm_action(prompt_message, default=False)`.
   - Prompts user for explicit confirmation (`[y/N]`) before dangerous operations like termination.

5. **Process Details View:**
   - Public interface `display_process_details(details)`.
   - Formats process metadata dictionary from Member 6 or handled error dictionaries.

6. **Status, Error, and Outcome Messages:**
   - Public interfaces `display_message(message, level="info")` and `display_action_result(result)`.
   - Handles structured action result dictionaries `{"success": bool, "message": str, "error": str, "pid": int}`.

7. **Refresh Coordination:**
   - Public interface `render_dashboard(processes, cpu_stats=None, memory_stats=None, sort_by=None, message=None, clear=True)`.
   - Helper `refresh_view(fetch_data_callback, clear=True)` for single-frame refresh.
   - Helper `run_refresh_loop(fetch_data_callback, interval=2.0, max_iterations=None, stop_check=None)` for continuous live monitoring mode.
   - Safe sleep slicing allowing immediate response to Ctrl+C without lag.

8. **Clean Exit and Portability:**
   - Pure standard library Python 3 (no third-party curses or TUI dependencies).
   - Fully compatible with Windows 11 console/PowerShell and Linux terminals.
   - `clear_screen()` checks `sys.stdout.isatty()` to prevent console pollution in non-interactive environments and test runners.

---

## 4. Public Functions & Expected Data Schemas

### A. `display_process_table(processes, sort_by=None)`
Renders an aligned terminal table.

**Expected `processes` schema (`list[dict]`):**
```python
[
    {
        "pid": 1234,              # int or None
        "name": "python.exe",     # str or None
        "status": "running",      # str or None
        "cpu_percent": 4.5,       # float, int, str ('Sampling...'), or None
        "memory_mb": 128.0,       # float, int, or None
        "memory_percent": 1.2,    # float, int, or None
        "thread_count": 6         # int or None
    },
    ...
]
```

### B. `display_system_summary(cpu_stats=None, memory_stats=None)`
Renders the system summary box.

**Expected `cpu_stats` schema (`dict` or `float`):**
```python
{
    "total_percent": 18.5,   # float or int (or 'cpu_percent' / 'percent')
    "cores": 8,              # int (optional)
    "status": "active"       # str: if 'sampling', displays 'Sampling...'
}
```

**Expected `memory_stats` schema (`dict`):**
```python
{
    "total_mb": 16384.0,     # float or int
    "used_mb": 8192.0,       # float or int
    "available_mb": 8192.0,  # float or int
    "percent": 50.0          # float or int
}
# Note: If byte values ('total', 'used', 'available') are provided,
# display.py will automatically convert them to MB.
```

### C. `display_process_details(details)`
Renders a process details card.

**Expected `details` schema (`dict` or `None`):**
```python
{
    "pid": 1234,
    "name": "example",
    "status": "running",
    "cpu_percent": 4.2,
    "memory_mb": 128.0,
    "memory_percent": 1.1,
    "thread_count": 6,
    "ppid": 1000,
    "username": "user",
    "create_time": "2026-10-12 10:00:00",
    "exe": "C:\\path\\example.exe",
    "cmdline": ["example.exe", "--arg"]
}
# Or on error:
{"error": "NoSuchProcess: process terminated before inspection"}
```

### D. `confirm_action(prompt_message, default=False) -> bool`
Prompts user: `{prompt_message} [y/N]: `  
Returns `True` if user enters `'y'` or `'yes'`, `False` otherwise.

### E. `display_action_result(result)`
Renders structured outcome from Member 6 or Member 7:
```python
{"success": True, "message": "Process terminated successfully.", "pid": 1234}
# or
{"success": False, "message": "Access denied.", "error": "AccessDenied", "pid": 1}
```

### F. `run_refresh_loop(fetch_data_callback, interval=2.0, max_iterations=None, stop_check=None)`
Coordinates live refresh loop.  
`fetch_data_callback` must return a tuple:
`(processes, cpu_stats, memory_stats, sort_by, message)`

---

## 5. Integration Guide for Member 1 (`main.py`)

Member 1 owns the application controller loop. Integrating Member 5's UI into `main.py` is straightforward:

```python
# Example snippet for Member 1's main.py:

from process_monitor import display
# Import services owned by other members when available:
# from process_monitor.monitor import get_process_list, get_cpu_stats, get_memory_stats
# from process_monitor.actions import search_processes, sort_processes, get_process_details, terminate_process

def fetch_data():
    # Call monitoring functions (Members 2, 3, 4)
    processes = get_process_list()
    cpu_stats = get_cpu_stats()
    memory_stats = get_memory_stats()
    return processes, cpu_stats, memory_stats, current_sort, status_message

def main():
    while True:
        # 1. Fetch current data
        procs, cpu, mem, sort_key, msg = fetch_data()

        # 2. Render dashboard frame using Member 5's display
        display.render_dashboard(procs, cpu, mem, sort_by=sort_key, message=msg, clear=True)

        # 3. Display menu and prompt user
        display.display_menu(current_sort=sort_key)
        choice = display.prompt_menu_choice()

        if choice == "1":
            # Refresh
            continue
        elif choice == "2":
            # Search (delegate to Member 6)
            query = display.prompt_input("Enter search query (name or PID): ")
            # procs = search_processes(procs, query)
        elif choice == "3":
            # Sort (delegate to Member 6)
            sort_field = display.prompt_input("Sort by (cpu_percent, memory_mb, pid, name): ")
            # procs = sort_processes(procs, sort_field)
        elif choice == "4":
            # View details (delegate to Member 6)
            pid = display.prompt_input("Enter PID for details: ")
            # details = get_process_details(pid)
            # display.display_process_details(details)
        elif choice == "5":
            # Safe termination (confirm with Member 5, execute with Member 7)
            pid = display.prompt_input("Enter PID to terminate: ")
            if display.confirm_action(f"Are you sure you want to terminate PID {pid}?"):
                # result = terminate_process(pid)
                # display.display_action_result(result)
                pass
        elif choice == "6":
            # Live auto-refresh mode
            display.run_refresh_loop(fetch_data, interval=2.0)
        elif choice == "7":
            # Clean exit
            display.display_message("Exiting Mini Process Monitor. Goodbye!", level="info")
            break
```

---

## 6. Expected Interfaces from Other Members

| Member | Module | Expected Function Signature | Purpose |
|---|---|---|---|
| Member 2 | `monitor.py` | `get_process_list() -> list[dict]` | Returns process records matching Section 9.1 schema |
| Member 3 | `monitor.py` | `get_cpu_stats() -> dict` | Returns system CPU utilization and sampling metadata |
| Member 4 | `monitor.py` | `get_memory_stats() -> dict` | Returns system memory metrics (total, used, available, percent) |
| Member 6 | `actions.py` | `search_processes(processes, query) -> list[dict]` | Filters process list |
| Member 6 | `actions.py` | `sort_processes(processes, sort_by) -> list[dict]` | Sorts process list |
| Member 6 | `actions.py` | `get_process_details(pid) -> dict` | Returns process details dictionary or `{"error": ...}` |
| Member 7 | `actions.py` | `terminate_process(pid) -> dict` | Performs confirmed termination, returns `{"success": bool, ...}` |

---

## 7. Verification and Test Results

### A. Automated Unit Tests (`tests/test_display.py`)
- **Command executed:** `python -m unittest discover -s tests -v`
- **Tests run:** 33 tests
- **Result:** 33 Passed, 0 Failed, 0 Errors (Execution time: ~0.004s)

**Checks verified:**
- All columns rendered with correct alignment and headers.
- Missing values (`None`) render as `"N/A"` without fabricating zero metrics.
- CPU sampling status renders `"Sampling..."`.
- Empty process list displays clear informative message.
- Long process names are safely truncated with an ellipsis.
- Input process records are never mutated.
- System summary handles both complete and sparse CPU/memory statistics.
- Menu options `[1]` through `[7]` are formatted correctly.
- Action results handle success and error structures cleanly.
- `confirm_action` safely evaluates user responses.
- `run_refresh_loop` cleanly terminates after `max_iterations` and upon `KeyboardInterrupt` (Ctrl+C).
- `clear_screen` executes only on TTY streams, ensuring safety during test runs and pipes.
- Standalone UI test harness initialization and exit.

### B. Interactive Standalone UI Preview (Using Temporary Test Records)
Member 5 provides a standalone interactive test harness so any team member can test the UI independently right now:
```powershell
python -m process_monitor.display
```
This launches a self-contained demonstration using synthetic test records matching the Section 9.1 schema, allowing interactive validation of table rendering, menu navigation, simulated search/sorting, details card presentation, termination confirmation prompt, auto-refresh mode, and clean exit.

---

## 8. Dependencies & Limitations

- **Dependencies:** Python 3 standard library only (`os`, `sys`, `shutil`, `time`, `datetime`, `typing`). No external packages or `psutil` required by Member 5.
- **Portability:** Tested on Windows 11 PowerShell and compatible with Linux terminals.
- **Outstanding Integration Dependencies:** Live process data depends on Members 2–4; Search/Sort/Details actions depend on Member 6; Termination logic depends on Member 7; Main coordinator loop depends on Member 1.
