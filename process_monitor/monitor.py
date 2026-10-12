"""Process enumeration for the Mini Process Monitor."""

import psutil


def get_process_list() -> list[dict]:
    """Return normalized information about accessible system processes.

    Missing metrics are represented by None. Processes that disappear
    during collection are skipped, and permission errors do not crash
    the entire process listing.
    """
    processes = []

    attributes = ["pid", "name", "status", "num_threads"]

    for proc in psutil.process_iter(attrs=attributes):
        try:
            info = proc.info

            processes.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "status": info.get("status"),
                    "cpu_percent": None,
                    "memory_mb": None,
                    "memory_percent": None,
                    "thread_count": info.get("num_threads"),
                }
            )

        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            # The process ended or became a zombie during collection.
            continue

        except psutil.AccessDenied:
            # Do not crash the entire listing because of permissions.
            continue

        except psutil.Error:
            # Handle other expected psutil-related failures.
            continue

    return processes




# Member 3: System CPU monitoring

_cpu_sampling_started = False


def get_cpu_stats() -> dict:
    """Return system-wide CPU usage and sampling metadata."""
    global _cpu_sampling_started

    cores = psutil.cpu_count(logical=True) or 1

    try:
        if not _cpu_sampling_started:
            psutil.cpu_percent(interval=None)
            _cpu_sampling_started = True
            return {
                "total_percent": None,
                "cores": cores,
                "status": "sampling",
            }

        return {
            "total_percent": psutil.cpu_percent(interval=None),
            "cores": cores,
            "status": "active",
        }

    except psutil.Error:
        return {
            "total_percent": None,
            "cores": cores,
            "status": "unavailable",
        }
