
from process_monitor.monitor import get_memory_stats, get_process_list

print("\n=== SYSTEM MEMORY ===")
print(get_memory_stats())

print("\n=== TOP 5 PROCESSES BY MEMORY USAGE===")
processes = get_process_list()
processes.sort(
    key=lambda p: p["memory_mb"] or 0,
    reverse=True
)

for p in processes[:5]:
    print(
        f"{p['name']} (PID {p['pid']}) | "
        f"{p['memory_mb']} MB | {p['memory_percent']}%"
    )


print("\n=== ALL PROCESSES BY MEMORY USAGE===")
processes = get_process_list()
processes.sort(
    key=lambda p: p["memory_mb"] or 0,
    reverse=True
)

for p in processes:
    print(
        f"{p['name']} (PID {p['pid']}) | "
        f"{p['memory_mb']} MB | {p['memory_percent']}%"
    )