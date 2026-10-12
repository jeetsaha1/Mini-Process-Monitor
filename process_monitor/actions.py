import os
import psutil

def terminate_process(pid: int, force: bool = False) -> dict:
    if pid == os.getpid():
        return {
            "status": "refused",
            "message": f"Self-protection trigger: Cannot terminate Mini Process Monitor itself (PID {pid}).",
            "error_type": "SelfProtection"
        }
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        if force:
            proc.kill()
            proc.wait(timeout=3)
            return {
                "status": "success",
                "message": f"Successfully force-killed process '{proc_name}' (PID {pid}).",
                "error_type": None
            }
        else:
            proc.terminate()
            proc.wait(timeout=3)
            return {
                "status": "success",
                "message": f"Successfully terminated process '{proc_name}' (PID {pid}).",
                "error_type": None
            }
    except psutil.NoSuchProcess:
        return {
            "status": "failed",
            "message": f"Process with PID {pid} no longer exists.",
            "error_type": "NoSuchProcess"
        }
    except psutil.AccessDenied:
        return {
            "status": "failed",
            "message": f"Access denied: Operating system permissions blocked terminating PID {pid}.",
            "error_type": "AccessDenied"
        }
    except psutil.ZombieProcess:
        return {
            "status": "failed",
            "message": f"Process PID {pid} is a zombie process and cannot be terminated directly.",
            "error_type": "ZombieProcess"
        }
    except psutil.TimeoutExpired:
        return {
            "status": "failed",
            "message": f"Termination request for PID {pid} timed out. Try force termination.",
            "error_type": "TimeoutExpired"
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": "UnexpectedError"
        }
