"""Process enumeration for the Mini Process Monitor."""

import psutil



def get_process_list() -> list[dict]:
    """Return normalized information about accessible system processes."""
    processes = []
    attributes = ["pid", "name", "status", "num_threads"]

    for proc in psutil.process_iter(attrs=attributes):
        try:
            info = proc.info

            memory_mb = None
            memory_percent = None

            try:
                memory_info = proc.memory_info()
                memory_mb = round(
                    memory_info.rss / (1024 ** 2), 2
                )
                memory_percent = round(
                    proc.memory_percent(), 2
                )
            except psutil.Error:
                # Keep the process even if memory access fails.
                pass

            processes.append({
                "pid": info.get("pid"),
                "name": info.get("name"),
                "status": info.get("status"),
                "cpu_percent": None,
                "memory_mb": memory_mb,
                "memory_percent": memory_percent,
                "thread_count": info.get("num_threads"),
            })

        except psutil.Error:
             # Skip processes that disappear or cannot be accessed.
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

# Member 4: Memory monitoring  
def get_memory_stats() -> dict:
    """Return system-wide memory usage statistics."""
    try:
        memory = psutil.virtual_memory()

        return {
            "total_mb": round(memory.total / (1024 ** 2), 2),
            "used_mb": round(memory.used / (1024 ** 2), 2),
            "available_mb": round(memory.available / (1024 ** 2), 2),
            "percent": memory.percent,
            "status": "active",
        }

    except psutil.Error:
        return {
            "total_mb": None,
            "used_mb": None,
            "available_mb": None,
            "percent": None,
            "status": "unavailable",
        }

def format_memory(bytes_value: int | None) -> str:
    """Convert bytes into a human-readable memory string."""
    if bytes_value is None:
        return "N/A"

    size = float(bytes_value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024

    return "N/A"

