
"""Process actions for Mini Process Monitor.

Includes searching, sorting, process details, and safe termination.
"""

import os
import math
import psutil


def search_processes(processes: list[dict], query: str) -> list[dict]:
    """Search by partial process name or exact PID."""
    query = query.strip().lower()

    if not query:
        return list(processes)

    return [
        process for process in processes
        if query in str(process.get("name") or "").lower()
        or query == str(process.get("pid", ""))
    ]


def sort_processes(
    processes: list[dict], sort_by: str = "cpu"
) -> list[dict]:
    """Sort processes, keeping missing or nonnumeric metrics last."""
    if not isinstance(sort_by, str):
        raise ValueError("sort_by must be cpu, memory, pid, or name")
        sort_by = sort_by.lower()

    aliases = {
        "cpu": "cpu_percent",
        "cpu_percent": "cpu_percent",
        "memory": "memory_mb",
        "memory_mb": "memory_mb",
        "pid": "pid",
        "name": "name",
    }

    if sort_by not in aliases:
        raise ValueError(
            "sort_by must be cpu, memory, pid, or name"
        )

    key = aliases[sort_by]
    descending = key in ("cpu_percent", "memory_mb")

    def valid_value(process):
        value = process.get(key)

        if key == "name":
            return value is not None

        if isinstance(value, bool) or value is None:
            return False

        try:
            number = float(value)
            return math.isfinite(number)
        except (TypeError, ValueError):
            return False

    available = [p for p in processes if valid_value(p)]
    unavailable = [p for p in processes if not valid_value(p)]

    def sort_key(process):
        value = process[key]
        if key == "name":
            return str(value).lower()
        if key in ("cpu_percent", "memory_mb", "pid"):
            return float(value)
        return value

    available.sort(key=sort_key, reverse=descending)
    return available + unavailable


def get_process_details(pid: int) -> dict:
    """Return process details using the UI's documented field names."""
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("PID must be a positive integer.")

    try:
        process = psutil.Process(pid)

        with process.oneshot():
            details = {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "ppid": process.ppid(),
                "thread_count": process.num_threads(),
                "create_time": process.create_time(),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(interval=None),
                "username": None,
                "exe": None,
                "cmdline": None,
            }

            try:
                details["username"] = process.username() or None
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass

            try:
                details["exe"] = process.exe() or None
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass

            try:
                details["cmdline"] = process.cmdline() or None
            except (psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return details

    except psutil.NoSuchProcess as exc:
        raise ValueError(f"Process {pid} no longer exists.") from exc
    except psutil.AccessDenied as exc:
        raise PermissionError(
            f"Access denied while inspecting process {pid}."
        ) from exc
    except psutil.ZombieProcess as exc:
        raise ValueError(f"Process {pid} is a zombie process.") from exc


def terminate_process(pid: int, force: bool = False) -> dict:
    """Terminate a process and return a UI-compatible result.

    The application controller must request explicit user confirmation
    before calling this function.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return {
            "success": False,
            "status": "failed",
            "message": "PID must be a positive integer.",
            "error": "InvalidPID",
            "error_type": "InvalidPID",
            "pid": pid if isinstance(pid, int) else None,
        }

    if pid == os.getpid():
        return {
            "success": False,
            "status": "refused",
            "message": (
                "Self-protection trigger: cannot terminate Mini Process Monitor."
            ),
            "error": "SelfProtection",
            "error_type": "SelfProtection",
            "pid": pid,
        }

    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()

        if force:
            proc.kill()
        else:
            proc.terminate()

        proc.wait(timeout=3)

        action = "force-killed" if force else "terminated"
        return {
            "success": True,
            "status": "success",
            "message": f"Successfully {action} '{proc_name}'.",
            "error": None,
            "error_type": None,
            "pid": pid,
        }

    except psutil.NoSuchProcess:
        error = "NoSuchProcess"
        message = f"Process {pid} no longer exists."
    except psutil.AccessDenied:
        error = "AccessDenied"
        message = f"Access denied while terminating PID {pid}."
    except psutil.ZombieProcess:
        error = "ZombieProcess"
        message = f"Process {pid} is a zombie process."
    except psutil.TimeoutExpired:
        error = "TimeoutExpired"
        message = f"Termination of PID {pid} timed out."
    except Exception as exc:
        error = "UnexpectedError"
        message = f"Unexpected termination error: {exc}"

    return {
        "success": False,
        "status": "failed",
        "message": message,
        "error": error,
        "error_type": error,
        "pid": pid,
    }