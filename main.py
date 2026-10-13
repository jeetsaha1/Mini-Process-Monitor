"""Main application controller for Mini Process Monitor."""


import time
import psutil

from process_monitor import actions, display, monitor


REFRESH_INTERVAL = 2.0
_process_cpu_cache = {}



def fetch_dashboard_data(sort_by="cpu", search_query=""):
    """Collect current process and system statistics."""
    processes = monitor.get_process_list()

    # CPU sampling needs time between measurements.
    # Reuse Process objects so CPU measurements have previous samples.
    active_pids = {process["pid"] for process in processes}

    for pid in list(_process_cpu_cache):
        if pid not in active_pids:
            del _process_cpu_cache[pid]

    for process in processes:
        if process.get("pid") == 0:
            process["cpu_percent"] = None
            continue
        try:
            pid = process["pid"]

            if pid not in _process_cpu_cache:
                proc = psutil.Process(pid)
                _process_cpu_cache[pid] = proc
                proc.cpu_percent(interval=None)
                process["cpu_percent"] = None
            else:
                process["cpu_percent"] = (
                    _process_cpu_cache[pid].cpu_percent(interval=None)
                )

        except (psutil.Error, TypeError, ValueError):
            _process_cpu_cache.pop(process.get("pid"), None)
            process["cpu_percent"] = None


    if search_query:
        processes = actions.search_processes(processes, search_query)

    try:
        processes = actions.sort_processes(processes, sort_by)
    except (ValueError, TypeError):
        sort_by = "cpu"

    cpu_stats = monitor.get_cpu_stats()
    memory_stats = monitor.get_memory_stats()

    return processes, cpu_stats, memory_stats, sort_by, None


def main():
    """Run the interactive process-monitor menu."""
    sort_by = "cpu"
    search_query = ""

    display.display_message(
        "Mini Process Monitor started. Choose an option from the menu.",
        level="success",
    )

    while True:
        data = fetch_dashboard_data(sort_by, search_query)
        processes, cpu_stats, memory_stats, sort_by, message = data

        display.render_dashboard(
            processes=processes,
            cpu_stats=cpu_stats,
            memory_stats=memory_stats,
            sort_by=sort_by,
            message=message,
            clear=False,
        )
        display.display_menu(current_sort=sort_by)

        choice = display.prompt_menu_choice()

        if choice == "1":
            display.display_message("Process table refreshed.")

        elif choice == "2":
            query = display.prompt_input(
                "Enter a process name or PID (blank clears search): "
            )
            if query is not None:
                search_query = query
                display.display_message(
                    "Search updated." if query else "Search cleared."
                )

        elif choice == "3":
            requested_sort = display.prompt_input(
                "Sort by cpu, memory, pid, or name: "
            )
            if requested_sort is not None:
                requested_sort = requested_sort.strip().lower()
                if requested_sort in (
                    "cpu", "cpu_percent", "memory",
                    "memory_mb", "pid", "name"
                ):
                    sort_by = requested_sort
                    display.display_message(
                        f"Sorting changed to {sort_by}.",
                        level="success",
                    )
                else:
                    display.display_message(
                        "Invalid sort option.", level="error"
                    )

        elif choice == "4":
            raw_pid = display.prompt_input(
                "Enter the PID to inspect: "
            )
            if raw_pid is not None:
                try:
                    details = actions.get_process_details(int(raw_pid))
                    display.display_process_details(details)
                except (ValueError, PermissionError, ProcessLookupError) as exc:
                    display.display_message(str(exc), level="error")

        elif choice == "5":
            raw_pid = display.prompt_input(
                "Enter the PID to terminate: "
            )
            if raw_pid is not None:
                try:
                    pid = int(raw_pid)
                    details = actions.get_process_details(pid)
                    name = details.get("name", "Unknown process")

                    confirmed = display.confirm_action(
                        f"Terminate '{name}' (PID {pid})?"
                    )
                    if confirmed:
                        result = actions.terminate_process(pid)
                        display.display_action_result(result)
                    else:
                        display.display_message(
                            "Termination cancelled.", level="warning"
                        )
                except (ValueError, PermissionError, ProcessLookupError) as exc:
                    display.display_message(str(exc), level="error")

        elif choice == "6":
            display.run_refresh_loop(
                lambda: fetch_dashboard_data(sort_by, search_query),
                interval=REFRESH_INTERVAL,
            )

        elif choice == "7":
            display.display_message(
                "Mini Process Monitor closed.", level="success"
            )
            break

        else:
            display.display_message(
                "Choose a menu option from 1 to 7.", level="error"
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Mini Process Monitor stopped.")
