"""Terminal UI and Refresh Module (Member 5).

This module implements the terminal user interface and refresh coordination
for the Mini Process Monitor project.

Responsibilities owned by Member 5:
- Terminal process-table rendering and column alignment.
- System summary presentation (CPU & Memory statistics).
- Menu presentation and user navigation.
- Refresh-related display behavior and controller coordination.
- Clear status, error, and informational message presentation.
- Clean exit behavior and graceful handling of interruptions (Ctrl+C).
- Documented handoff contract for Member 1 (controller) integration.

Ownership boundaries (Mandatory OS project rules):
- Does NOT collect process or system metrics (owned by Members 2, 3, 4).
- Does NOT perform underlying search, sort, or detail queries (owned by Member 6).
- Does NOT terminate processes (owned by Member 7).
- Does NOT own the main application controller loop (owned by Member 1).
- Does NOT depend on psutil directly; consumes agreed data schemas via parameters.
"""

from datetime import datetime
import os
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Missing value and sampling display markers
MISSING_VALUE_MARKER: str = "N/A"
SAMPLING_MARKER: str = "Sampling..."
DEFAULT_REFRESH_INTERVAL: float = 2.0


# ============================================================================
# 1. Formatting Helpers (Pure functions, no external dependencies)
# ============================================================================

def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, appending an ellipsis if truncated.

    Args:
        text: The string to truncate.
        max_length: Maximum allowed character width.

    Returns:
        The original or truncated string.
    """
    if text is None:
        return MISSING_VALUE_MARKER
    text_str = str(text)
    if len(text_str) <= max_length:
        return text_str
    if max_length <= 3:
        return text_str[:max_length]
    return text_str[:max_length - 3] + "..."


def format_pid(pid: Optional[int]) -> str:
    """Format a process ID for display."""
    if pid is None:
        return MISSING_VALUE_MARKER
    try:
        return str(int(pid))
    except (ValueError, TypeError):
        return str(pid)


def format_cpu_percent(cpu: Optional[Union[float, int, str]]) -> str:
    """Format CPU utilization.

    Preserves the sampling rule: if CPU measurement is in a warm-up or
    sampling state, displays 'Sampling...' rather than misleading '0.0%'
    or an unhandled exception.
    """
    if cpu is None:
        return MISSING_VALUE_MARKER
    if isinstance(cpu, str):
        if "sampl" in cpu.lower() or "warm" in cpu.lower():
            return SAMPLING_MARKER
        return cpu
    if isinstance(cpu, (int, float)):
        return f"{cpu:.1f}%"
    return str(cpu)


def format_memory_mb(memory_mb: Optional[Union[float, int]]) -> str:
    """Format resident memory in megabytes."""
    if memory_mb is None:
        return MISSING_VALUE_MARKER
    if isinstance(memory_mb, (int, float)):
        return f"{memory_mb:.1f}"
    return str(memory_mb)


def format_memory_percent(mem_percent: Optional[Union[float, int]]) -> str:
    """Format memory percentage."""
    if mem_percent is None:
        return MISSING_VALUE_MARKER
    if isinstance(mem_percent, (int, float)):
        return f"{mem_percent:.1f}%"
    return str(mem_percent)


def format_thread_count(threads: Optional[Union[int, str]]) -> str:
    """Format thread count."""
    if threads is None:
        return MISSING_VALUE_MARKER
    try:
        return str(int(threads))
    except (ValueError, TypeError):
        return str(threads)


def format_status(status: Optional[str]) -> str:
    """Format process execution status string."""
    if not status:
        return MISSING_VALUE_MARKER
    return str(status).strip()


# ============================================================================
# 2. Process Table Rendering
# ============================================================================

def format_process_table(
    processes: List[Dict[str, Any]],
    sort_by: Optional[str] = None
) -> str:
    """Format a list of process records into an aligned terminal table string.

    This function does NOT retrieve processes or perform sorting; it strictly
    renders the supplied records according to the agreed process-record schema.

    Standard record keys supported:
        - 'pid': int or None
        - 'name': str or None
        - 'status': str or None
        - 'cpu_percent': float, int, str ('Sampling...'), or None
        - 'memory_mb': float, int, or None
        - 'memory_percent': float, int, or None
        - 'thread_count': int or None

    Args:
        processes: List of process dictionaries to display.
        sort_by: Optional string naming the current active sort column.

    Returns:
        Formatted multi-line table string ready for terminal display.
    """
    # Determine responsive terminal width (default 80 columns)
    try:
        terminal_width = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        terminal_width = 80

    # Fixed column widths
    w_pid = 7
    w_status = 12
    w_cpu = 11      # Accommodates "Sampling..."
    w_mem_mb = 10
    w_mem_pct = 8
    w_threads = 8

    # Dynamic name column width (bounded between 16 and 36 chars)
    fixed_overhead = w_pid + w_status + w_cpu + w_mem_mb + w_mem_pct + w_threads + 22
    w_name = max(16, min(36, terminal_width - fixed_overhead))

    # Construct border separators
    # Format: +-------+----------------------+------------+-------------+------------+----------+----------+
    border = (
        f"+-{'-' * w_pid}-+-"
        f"{'-' * w_name}-+-"
        f"{'-' * w_status}-+-"
        f"{'-' * w_cpu}-+-"
        f"{'-' * w_mem_mb}-+-"
        f"{'-' * w_mem_pct}-+-"
        f"{'-' * w_threads}-+"
    )

    # Header line
    headers = (
        f"| {'PID':>{w_pid}} | "
        f"{'Name':<{w_name}} | "
        f"{'Status':<{w_status}} | "
        f"{'CPU %':>{w_cpu}} | "
        f"{'Mem (MB)':>{w_mem_mb}} | "
        f"{'Mem %':>{w_mem_pct}} | "
        f"{'Threads':>{w_threads}} |"
    )

    lines: List[str] = []

    # Table Title with sorting indication if applicable
    title = "PROCESS TABLE"
    if sort_by:
        title += f" [Sorted by: {sort_by}]"
    lines.append(f"=== {title} ({len(processes)} processes) ===")
    lines.append(border)
    lines.append(headers)
    lines.append(border)

    if not processes:
        empty_msg = "No processes to display. (Empty record set provided)"
        table_inner_width = len(border) - 4
        lines.append(f"| {empty_msg:<{table_inner_width}} |")
        lines.append(border)
        return "\n".join(lines)

    for proc in processes:
        # Guard against None row or unexpected types
        if not isinstance(proc, dict):
            continue

        raw_pid = proc.get("pid")
        raw_name = proc.get("name")
        raw_status = proc.get("status")
        raw_cpu = proc.get("cpu_percent")
        raw_mem_mb = proc.get("memory_mb")
        raw_mem_pct = proc.get("memory_percent")
        raw_threads = proc.get("thread_count")

        pid_str = format_pid(raw_pid)
        name_str = truncate_text(raw_name if raw_name is not None else MISSING_VALUE_MARKER, w_name)
        status_str = truncate_text(format_status(raw_status), w_status)
        cpu_str = format_cpu_percent(raw_cpu)
        mem_mb_str = format_memory_mb(raw_mem_mb)
        mem_pct_str = format_memory_percent(raw_mem_pct)
        threads_str = format_thread_count(raw_threads)

        row = (
            f"| {pid_str:>{w_pid}} | "
            f"{name_str:<{w_name}} | "
            f"{status_str:<{w_status}} | "
            f"{cpu_str:>{w_cpu}} | "
            f"{mem_mb_str:>{w_mem_mb}} | "
            f"{mem_pct_str:>{w_mem_pct}} | "
            f"{threads_str:>{w_threads}} |"
        )
        lines.append(row)

    lines.append(border)
    return "\n".join(lines)


def display_process_table(
    processes: List[Dict[str, Any]],
    sort_by: Optional[str] = None
) -> None:
    """Render the supplied process records to standard output.

    Public interface agreed in Section 9 of the project plan.
    Does NOT collect processes or perform sorting internally.

    Args:
        processes: List of process records from the monitoring service.
        sort_by: Optional active sort key label.
    """
    print(format_process_table(processes, sort_by=sort_by))


# ============================================================================
# 3. System Summary Presentation
# ============================================================================

def format_system_summary(
    cpu_stats: Optional[Dict[str, Any]] = None,
    memory_stats: Optional[Dict[str, Any]] = None
) -> str:
    """Format system-wide CPU and memory statistics into a summary block.

    Consumes data returned by the monitoring layer (Members 3 and 4).
    Handles missing, sampling, or partially populated values cleanly with 'N/A'.

    Args:
        cpu_stats: Dict containing CPU stats (e.g. 'total_percent', 'cores', 'status').
        memory_stats: Dict containing memory stats (e.g. 'total_mb', 'used_mb',
                      'available_mb', 'percent').

    Returns:
        Formatted multi-line summary string.
    """
    # CPU summary resolution
    cpu_display = MISSING_VALUE_MARKER
    if cpu_stats is not None:
        if isinstance(cpu_stats, (int, float)):
            cpu_display = f"{cpu_stats:.1f}%"
        elif isinstance(cpu_stats, dict):
            # Check for sampling status
            status_val = cpu_stats.get("status", "")
            if isinstance(status_val, str) and "sampl" in status_val.lower():
                cpu_display = SAMPLING_MARKER
            else:
                total_pct = cpu_stats.get("total_percent")
                if total_pct is None:
                    total_pct = cpu_stats.get("cpu_percent")
                if total_pct is None:
                    total_pct = cpu_stats.get("percent")

                if total_pct is not None and isinstance(total_pct, (int, float)):
                    cpu_display = f"{total_pct:.1f}%"
                    cores = cpu_stats.get("cores") or cpu_stats.get("cpu_count")
                    if cores is not None:
                        cpu_display += f" ({cores} logical cores)"
                elif isinstance(total_pct, str) and "sampl" in total_pct.lower():
                    cpu_display = SAMPLING_MARKER

    # Memory summary resolution
    mem_display = MISSING_VALUE_MARKER
    if memory_stats is not None:
        if isinstance(memory_stats, dict):
            # Handle either MB values or byte values
            total = memory_stats.get("total_mb")
            used = memory_stats.get("used_mb")
            avail = memory_stats.get("available_mb")
            pct = memory_stats.get("percent")

            # Fallback if bytes were supplied
            if total is None and "total" in memory_stats:
                total = memory_stats["total"] / (1024 * 1024)
            if used is None and "used" in memory_stats:
                used = memory_stats["used"] / (1024 * 1024)
            if avail is None and "available" in memory_stats:
                avail = memory_stats["available"] / (1024 * 1024)

            parts: List[str] = []
            if used is not None and total is not None:
                parts.append(f"{used:,.1f} MB / {total:,.1f} MB")
            elif used is not None:
                parts.append(f"Used: {used:,.1f} MB")
            elif total is not None:
                parts.append(f"Total: {total:,.1f} MB")

            if pct is not None:
                parts.append(f"({pct:.1f}%)")

            if avail is not None:
                parts.append(f"| Available: {avail:,.1f} MB")

            if parts:
                mem_display = " ".join(parts)

    divider = "=" * 76
    return (
        f"{divider}\n"
        f" SYSTEM SUMMARY\n"
        f"   CPU Usage:    {cpu_display}\n"
        f"   Memory Usage: {mem_display}\n"
        f"{divider}"
    )


def display_system_summary(
    cpu_stats: Optional[Dict[str, Any]] = None,
    memory_stats: Optional[Dict[str, Any]] = None
) -> None:
    """Print the system summary to the terminal.

    Args:
        cpu_stats: System CPU statistics dictionary.
        memory_stats: System memory statistics dictionary.
    """
    print(format_system_summary(cpu_stats=cpu_stats, memory_stats=memory_stats))


# ============================================================================
# 4. Process Details View
# ============================================================================

def format_process_details(details: Optional[Dict[str, Any]]) -> str:
    """Format process details returned by Member 6 into a readable card.

    Args:
        details: Dictionary containing detailed process attributes, or None.

    Returns:
        Formatted multi-line detail card string.
    """
    if details is None:
        return "[INFO] No details available for the requested process."

    if not isinstance(details, dict):
        return f"[INFO] Details: {details}"

    # Handle error responses from Member 6
    if "error" in details:
        err_msg = details.get("error", "Unknown error")
        return f"[ERROR] Could not retrieve process details: {err_msg}"

    border = "=" * 70
    lines: List[str] = [
        border,
        f" PROCESS DETAILS: PID {details.get('pid', MISSING_VALUE_MARKER)}",
        border,
    ]

    field_mappings: List[Tuple[str, str, Callable[[Any], str]]] = [
        ("pid", "Process ID (PID)", format_pid),
        ("name", "Process Name", lambda v: str(v) if v is not None else MISSING_VALUE_MARKER),
        ("status", "Status", format_status),
        ("cpu_percent", "CPU Usage", format_cpu_percent),
        ("memory_mb", "Memory (RSS MB)", format_memory_mb),
        ("memory_percent", "Memory Percentage", format_memory_percent),
        ("thread_count", "Thread Count", format_thread_count),
        ("ppid", "Parent PID (PPID)", format_pid),
        ("username", "Owner / User", lambda v: str(v) if v is not None else MISSING_VALUE_MARKER),
        ("create_time", "Created Time", lambda v: str(v) if v is not None else MISSING_VALUE_MARKER),
        ("exe", "Executable Path", lambda v: str(v) if v is not None else MISSING_VALUE_MARKER),
        ("cmdline", "Command Line", lambda v: " ".join(v) if isinstance(v, list) else (str(v) if v is not None else MISSING_VALUE_MARKER)),
    ]

    handled_keys = set()
    for key, label, formatter in field_mappings:
        if key in details:
            handled_keys.add(key)
            formatted_val = formatter(details[key])
            lines.append(f"  {label:<24}: {formatted_val}")

    # Display any remaining custom keys provided by Member 6
    for key, value in details.items():
        if key not in handled_keys:
            lines.append(f"  {str(key).replace('_', ' ').title():<24}: {value if value is not None else MISSING_VALUE_MARKER}")

    lines.append(border)
    return "\n".join(lines)


def display_process_details(details: Optional[Dict[str, Any]]) -> None:
    """Print the formatted process details to standard output."""
    print(format_process_details(details))


# ============================================================================
# 5. Menu Presentation and UI Navigation
# ============================================================================

def format_menu(current_sort: Optional[str] = None) -> str:
    """Format the interactive terminal menu string.

    Args:
        current_sort: Optional name of the currently active sort column.

    Returns:
        Formatted menu string.
    """
    sort_info = f" (Active: {current_sort})" if current_sort else ""
    return (
        "======================== MENU OPTIONS ========================\n"
        " [1] Refresh Process Table\n"
        " [2] Search Processes (by Name or PID)\n"
        f" [3] Sort Process Table{sort_info}\n"
        " [4] View Process Details\n"
        " [5] Terminate Process (Safe Confirmation Request)\n"
        " [6] Live Auto-Refresh Mode\n"
        " [7] Exit Mini Process Monitor\n"
        "=============================================================="
    )


def display_menu(current_sort: Optional[str] = None) -> None:
    """Display the main menu to the user."""
    print(format_menu(current_sort=current_sort))


def prompt_menu_choice(prompt_text: str = "Select an option [1-7]: ") -> str:
    """Prompt the user for a menu selection safely.

    Handles KeyboardInterrupt and EOFError gracefully without crashing.

    Args:
        prompt_text: Text displayed for the input prompt.

    Returns:
        Sanitized input string, or '7' on Ctrl+C / EOF to request clean exit.
    """
    try:
        choice = input(prompt_text).strip()
        return choice
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Interrupt received. Exiting menu...")
        return "7"


def prompt_input(
    prompt_text: str,
    default: Optional[str] = None
) -> Optional[str]:
    """Safely prompt the user for arbitrary string input (e.g. search query, PID).

    Args:
        prompt_text: Prompt message to display.
        default: Optional default value if user enters empty input.

    Returns:
        The entered string, default value, or None if cancelled via Ctrl+C / EOF.
    """
    try:
        val = input(prompt_text).strip()
        if not val and default is not None:
            return default
        return val
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Input cancelled by user.")
        return None


def confirm_action(
    prompt_message: str,
    default: bool = False
) -> bool:
    """Prompt the user for explicit confirmation before executing an action.

    Mandatory for safe process termination integration (Member 7).
    Requires explicit 'y' or 'yes' input.

    Args:
        prompt_message: Confirmation explanation displaying the target process and PID.
        default: Default answer if empty input is entered (defaults to False for safety).

    Returns:
        True if the user confirmed, False otherwise.
    """
    indicator = "[y/N]" if not default else "[Y/n]"
    full_prompt = f"{prompt_message} {indicator}: "

    try:
        ans = input(full_prompt).strip().lower()
        if not ans:
            return default
        return ans in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Action cancelled.")
        return False


# ============================================================================
# 6. Status, Informational, and Error Message Presentation
# ============================================================================

def format_message(message: str, level: str = "info") -> str:
    """Format a status or error notification.

    Args:
        message: Notification message text.
        level: Severity level ('info', 'success', 'warning', 'error').

    Returns:
        Prefixed message string.
    """
    tag = level.upper()
    return f"[{tag}] {message}"


def display_message(message: str, level: str = "info") -> None:
    """Display a status or error message to standard output."""
    print(format_message(message=message, level=level))


def format_action_result(result: Any) -> str:
    """Format structured action results (from Members 6 or 7).

    Agreed contract from Section 9.3:
        Result dictionary containing 'success' (bool), 'message' (str),
        and optional 'error' (str) or 'pid' (int).

    Args:
        result: Dictionary or string containing the result of an action.

    Returns:
        Formatted outcome string.
    """
    if result is None:
        return "[INFO] Action completed."

    if isinstance(result, str):
        return f"[INFO] {result}"

    if isinstance(result, dict):
        success = result.get("success", True)
        msg = result.get("message", "Action finished.")
        err = result.get("error")
        pid = result.get("pid")

        pid_prefix = f"PID {pid}: " if pid is not None else ""
        if success:
            return f"[SUCCESS] {pid_prefix}{msg}"
        else:
            detail = f" (Error: {err})" if err else ""
            return f"[ERROR] {pid_prefix}{msg}{detail}"

    return f"[INFO] {str(result)}"


def display_action_result(result: Any) -> None:
    """Print a structured action result."""
    print(format_action_result(result))


# ============================================================================
# 7. Screen Clearing & Cross-Platform Terminal Operations
# ============================================================================

def clear_screen() -> None:
    """Clear terminal screen in a cross-platform manner.

    Safe on Windows 11 and Linux. Avoids running clear/cls in non-interactive
    or non-TTY environments (such as unit test runners or file redirects).
    """
    # Only clear if standard output is an interactive terminal
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


# ============================================================================
# 8. Integrated Dashboard Rendering
# ============================================================================

def render_dashboard(
    processes: List[Dict[str, Any]],
    cpu_stats: Optional[Dict[str, Any]] = None,
    memory_stats: Optional[Dict[str, Any]] = None,
    sort_by: Optional[str] = None,
    message: Optional[str] = None,
    clear: bool = True
) -> None:
    """Render a complete dashboard frame (header, summary, status, process table).

    Args:
        processes: List of process records to display.
        cpu_stats: System CPU statistics dictionary.
        memory_stats: System memory statistics dictionary.
        sort_by: Active sort key label.
        message: Optional status or feedback message banner.
        clear: Whether to clear the terminal screen before rendering.
    """
    if clear:
        clear_screen()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"============================================================================\n"
        f" MINI PROCESS MONITOR  |  Terminal UI (Member 5)  |  {timestamp}\n"
        f"============================================================================"
    )
    print(header)
    print(format_system_summary(cpu_stats=cpu_stats, memory_stats=memory_stats))

    if message:
        print(f"\n{message}\n")

    print(format_process_table(processes=processes, sort_by=sort_by))


# ============================================================================
# 9. Refresh Coordination and Controller Integration Helpers
# ============================================================================

def refresh_view(
    fetch_data_callback: Callable[[], Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]],
    clear: bool = True
) -> None:
    """Execute a single refresh cycle by invoking the controller callback and rendering.

    Args:
        fetch_data_callback: Callback supplied by Member 1 returning:
                             (processes, cpu_stats, memory_stats, sort_by, message)
        clear: Whether to clear the screen before rendering.
    """
    try:
        data = fetch_data_callback()
        if isinstance(data, (tuple, list)) and len(data) >= 3:
            procs = data[0]
            cpu = data[1]
            mem = data[2]
            sort_by = data[3] if len(data) > 3 else None
            msg = data[4] if len(data) > 4 else None
            render_dashboard(
                processes=procs,
                cpu_stats=cpu,
                memory_stats=mem,
                sort_by=sort_by,
                message=msg,
                clear=clear
            )
        else:
            display_message(
                "fetch_data_callback must return at least (processes, cpu_stats, memory_stats).",
                level="error"
            )
    except Exception as exc:
        display_message(f"Refresh failed: {exc}", level="error")


def run_refresh_loop(
    fetch_data_callback: Callable[[], Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]],
    interval: float = DEFAULT_REFRESH_INTERVAL,
    max_iterations: Optional[int] = None,
    stop_check: Optional[Callable[[], bool]] = None
) -> None:
    """Coordinate a continuous live refresh loop for the terminal display.

    This helper can be invoked by Member 1's controller when entering live
    monitoring mode. It cleanly coordinates periodic re-rendering and
    guarantees safe, graceful exit upon Ctrl+C (KeyboardInterrupt) or stop condition.

    Args:
        fetch_data_callback: Callback returning latest system and process data.
        interval: Refresh interval in seconds (default ~2.0s).
        max_iterations: Optional maximum frame count (useful for testing).
        stop_check: Optional callable returning True when the loop should exit.
    """
    iteration = 0
    print("[INFO] Starting live refresh mode. Press Ctrl+C to return to menu...")
    time.sleep(0.5)

    try:
        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
            if stop_check is not None and stop_check():
                break

            refresh_view(fetch_data_callback, clear=True)
            print(f"\n[Live Mode: Refresh interval {interval:.1f}s | Press Ctrl+C to stop]")

            iteration += 1

            # Sleep in short slices to respond quickly to Ctrl+C or stop_check
            sleep_slices = max(1, int(interval / 0.1))
            slice_duration = interval / sleep_slices
            for _ in range(sleep_slices):
                if stop_check is not None and stop_check():
                    break
                time.sleep(slice_duration)

    except KeyboardInterrupt:
        print("\n[INFO] Live refresh stopped by user (Ctrl+C). Returning to menu...")
    except Exception as exc:
        display_message(f"Error during refresh loop: {exc}", level="error")
    finally:
        # Clean terminal separation
        print("[INFO] Clean exit from refresh mode.")


# ============================================================================
# 10. Standalone UI Test Harness (Temporary Test Records Only)
# ============================================================================

def _run_standalone_ui_test() -> None:
    """Run an interactive UI test session using synthetic test records.

    This test harness is used exclusively for testing Member 5's deliverables
    independently before other members have completed their modules.
    It does NOT collect real system metrics or perform actual OS operations.
    """
    print("\n" + "=" * 76)
    print(" [MEMBER 5 UI TEST HARNESS] Mini Process Monitor - Terminal UI Preview")
    print(" Using temporary synthetic records for independent UI verification.")
    print(" Real process collection, sorting, and termination are owned by other members.")
    print("=" * 76 + "\n")

    # Synthetic process records matching Section 9.1 schema
    test_processes = [
        {
            "pid": 101,
            "name": "system",
            "status": "running",
            "cpu_percent": 0.8,
            "memory_mb": 24.5,
            "memory_percent": 0.2,
            "thread_count": 140,
        },
        {
            "pid": 450,
            "name": "svchost.exe",
            "status": "running",
            "cpu_percent": 2.1,
            "memory_mb": 85.2,
            "memory_percent": 0.5,
            "thread_count": 28,
        },
        {
            "pid": 1120,
            "name": "explorer.exe",
            "status": "running",
            "cpu_percent": 4.5,
            "memory_mb": 195.4,
            "memory_percent": 1.2,
            "thread_count": 42,
        },
        {
            "pid": 2048,
            "name": "python_test_runner.exe",
            "status": "running",
            "cpu_percent": 18.2,
            "memory_mb": 112.0,
            "memory_percent": 0.7,
            "thread_count": 6,
        },
        {
            "pid": 3312,
            "name": "warming_daemon",
            "status": "sleeping",
            "cpu_percent": "Sampling...",
            "memory_mb": 42.0,
            "memory_percent": 0.3,
            "thread_count": 2,
        },
        {
            "pid": 4900,
            "name": "sparse_edge_case",
            "status": None,
            "cpu_percent": None,
            "memory_mb": None,
            "memory_percent": None,
            "thread_count": None,
        },
        {
            "pid": 5820,
            "name": "very_long_process_name_for_truncation_test.exe",
            "status": "running",
            "cpu_percent": 1.1,
            "memory_mb": 64.0,
            "memory_percent": 0.4,
            "thread_count": 4,
        },
    ]

    test_cpu = {"total_percent": 26.7, "cores": 8, "status": "active"}
    test_mem = {
        "total_mb": 16384.0,
        "used_mb": 8192.0,
        "available_mb": 8192.0,
        "percent": 50.0,
    }

    current_procs = list(test_processes)
    current_sort: Optional[str] = None
    status_msg: Optional[str] = "[TEST INFO] Initialized with 7 synthetic test records."

    while True:
        render_dashboard(
            processes=current_procs,
            cpu_stats=test_cpu,
            memory_stats=test_mem,
            sort_by=current_sort,
            message=status_msg,
            clear=False,
        )
        display_menu(current_sort=current_sort)
        choice = prompt_menu_choice()

        status_msg = None

        if choice == "1":
            # Refresh view
            current_procs = list(test_processes)
            status_msg = "[TEST INFO] Process table refreshed (test data reloaded)."

        elif choice == "2":
            # Search testing
            query = prompt_input("Enter search query (PID or Name) [Test harness filter]: ")
            if query:
                q_lower = query.lower()
                current_procs = [
                    p for p in test_processes
                    if q_lower in str(p.get("pid", "")).lower()
                    or q_lower in str(p.get("name", "")).lower()
                ]
                status_msg = f"[TEST INFO] Search filter for '{query}' returned {len(current_procs)} records."

        elif choice == "3":
            # Sort testing
            sort_key = prompt_input("Enter sort key (cpu_percent, memory_mb, pid, name): ")
            if sort_key in ("cpu_percent", "memory_mb", "pid", "name"):
                current_sort = sort_key
                def _safe_sort_val(p: Dict[str, Any]) -> Any:
                    val = p.get(sort_key)
                    if val is None or isinstance(val, str):
                        return -1 if sort_key in ("cpu_percent", "memory_mb", "pid") else ""
                    return val
                current_procs = sorted(current_procs, key=_safe_sort_val, reverse=(sort_key in ("cpu_percent", "memory_mb")))
                status_msg = f"[TEST INFO] Table sorted by '{sort_key}' (simulated)."
            else:
                status_msg = f"[TEST WARNING] Unknown sort key '{sort_key}'. Please choose cpu_percent, memory_mb, pid, or name."

        elif choice == "4":
            # Details testing
            pid_str = prompt_input("Enter PID for details test [e.g. 2048 or 4900]: ")
            if pid_str and pid_str.isdigit():
                target_pid = int(pid_str)
                matched = next((p for p in test_processes if p["pid"] == target_pid), None)
                if matched:
                    details_payload = dict(matched)
                    details_payload.update({
                        "ppid": 1000,
                        "username": "os_test_user",
                        "create_time": "2026-10-12 12:00:00",
                        "exe": f"C:\\Program Files\\Test\\{matched.get('name', 'app.exe')}",
                        "cmdline": [str(matched.get("name")), "--test-mode"],
                    })
                    display_process_details(details_payload)
                else:
                    display_process_details({"error": f"NoSuchProcess: PID {target_pid} not in test set."})
            else:
                display_message("Invalid PID entered.", level="warning")
            prompt_input("\nPress Enter to return to menu...")

        elif choice == "5":
            # Termination confirmation testing
            pid_str = prompt_input("Enter PID to test safe termination [e.g. 2048]: ")
            if pid_str and pid_str.isdigit():
                target_pid = int(pid_str)
                matched = next((p for p in test_processes if p["pid"] == target_pid), None)
                proc_name = matched["name"] if matched else f"PID_{target_pid}"
                confirmed = confirm_action(
                    f"Are you sure you want to request termination of process '{proc_name}' (PID: {target_pid})?"
                )
                if confirmed:
                    display_action_result({
                        "success": True,
                        "message": f"Termination request confirmed in UI for '{proc_name}'.",
                        "pid": target_pid,
                    })
                else:
                    display_action_result({
                        "success": False,
                        "message": "Termination was aborted by the user.",
                        "pid": target_pid,
                    })
            else:
                display_message("Invalid PID entered.", level="warning")
            prompt_input("\nPress Enter to return to menu...")

        elif choice == "6":
            # Live refresh testing (simulated loop with test data)
            def _test_fetch():
                return current_procs, test_cpu, test_mem, current_sort, None
            run_refresh_loop(_test_fetch, interval=2.0, max_iterations=3)
            prompt_input("\nPress Enter to return to menu...")

        elif choice == "7":
            display_message("Exiting standalone UI test harness. Goodbye!", level="info")
            break

        else:
            display_message(f"Invalid option '{choice}'. Please select [1-7].", level="warning")


if __name__ == "__main__":
    _run_standalone_ui_test()

