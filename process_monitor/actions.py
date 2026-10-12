
"""Search and sorting utilities for Mini Process Monitor."""

import psutil


def search_processes(processes: list[dict], query: str) -> list[dict]:
    """Search processes by name or exact PID."""
    query = query.strip().lower()

    if not query:
        return list(processes)

    results = []

    for process in processes:
        name = str(process.get("name") or "").lower()
        pid = str(process.get("pid", ""))

        if query in name or query == pid:
            results.append(process)

    return results


def sort_processes(
    processes: list[dict], sort_by: str = "cpu"
) -> list[dict]:
    """Sort processes while keeping missing values at the bottom."""
    sort_by = sort_by.lower()

    sort_options = {
        "cpu": "cpu_percent",
        "memory": "memory_mb",
        "pid": "pid",
        "name": "name",
    }

    if sort_by not in sort_options:
        raise ValueError(
            "sort_by must be cpu, memory, pid, or name"
        )

    key = sort_options[sort_by]
    reverse = sort_by in ("cpu", "memory")

    available = [
        p for p in processes if p.get(key) is not None
    ]
    unavailable = [
        p for p in processes if p.get(key) is None
    ]

    def sort_key(process):
        value = process[key]

        if sort_by == "name":
            return str(value).lower()

        return value

    available.sort(key=sort_key, reverse=reverse)

    return available + unavailable


def get_process_details(pid: int) -> dict:
    """Return details for a process identified by PID."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("PID must be a positive integer.")

    try:
        process = psutil.Process(pid)

        with process.oneshot():
            details = {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "parent_pid": process.ppid(),
                "thread_count": process.num_threads(),
                "created_at": process.create_time(),
                "memory_mb": (
                    process.memory_info().rss / (1024 * 1024)
                ),
                "executable": None,
                "command_line": None,
            }

            try:
                details["executable"] = process.exe() or None
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass

            try:
                details["command_line"] = process.cmdline() or None
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return details

    except psutil.NoSuchProcess as exc:
        raise ValueError(
            f"Process {pid} no longer exists."
        ) from exc

    except psutil.AccessDenied as exc:
        raise PermissionError(
            f"Access denied while inspecting process {pid}."
        ) from exc

    except psutil.ZombieProcess as exc:
        raise ValueError(
            f"Process {pid} is a zombie process."
        ) from exc
