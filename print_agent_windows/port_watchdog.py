"""
Port Watchdog — prevents Error 10048 (address already in use)
by killing any leftover process on the agent port before starting.

Standalone module that can be imported by both agent_windows.py and agent_linux.py.
"""

import subprocess
import sys
import logging
import os
import time

logger = logging.getLogger(__name__)


def force_free_port(port: int, max_retries: int = 3) -> bool:
    """
    Free a TCP port by killing whatever process is using it.
    Returns True if the port is free, False if it cannot be freed.
    """
    if sys.platform != 'win32':
        return _free_port_linux(port)

    for attempt in range(1, max_retries + 1):
        pid = _find_pid_on_port_windows(port)
        if not pid:
            logger.info(f"✅ Port {port} is free.")
            return True

        logger.warning(f"⚠️  Port {port} in use by PID {pid} (attempt {attempt}/{max_retries})")
        _kill_pid_windows(pid)
        time.sleep(1)

    # Final check
    if not _find_pid_on_port_windows(port):
        logger.info(f"✅ Port {port} freed after retries.")
        return True

    logger.error(f"❌ Cannot free port {port}. Close the program manually.")
    return False


def _find_pid_on_port_windows(port: int):
    """Find the PID using a port on Windows."""
    # Method 1: netstat
    try:
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'TCP'],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid > 0:
                    return pid
    except Exception as e:
        logger.debug(f"netstat failed: {e}")

    # Method 2: PowerShell fallback
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             f"(Get-NetTCPConnection -LocalPort {port} -State Listen "
             f"-ErrorAction SilentlyContinue).OwningProcess"],
            capture_output=True, text=True, timeout=10,
        )
        pid_str = result.stdout.strip().split('\n')[0].strip()
        if pid_str and pid_str.isdigit() and int(pid_str) > 0:
            return int(pid_str)
    except Exception:
        pass

    return None


def _kill_pid_windows(pid: int):
    """Force-kill a process on Windows."""
    try:
        if pid == os.getpid():
            return
        subprocess.run(
            ['taskkill', '/F', '/PID', str(pid)],
            capture_output=True, timeout=10,
        )
        logger.info(f"🔪 Killed PID {pid}")
    except Exception as e:
        logger.warning(f"Could not kill PID {pid}: {e}")


def _free_port_linux(port: int) -> bool:
    """Free a port on Linux using fuser."""
    try:
        result = subprocess.run(
            ['fuser', f'{port}/tcp'],
            capture_output=True, text=True, timeout=5,
        )
        pids = result.stdout.strip().split()
        if not pids:
            logger.info(f"✅ Port {port} is free.")
            return True

        for pid_str in pids:
            pid_str = pid_str.strip()
            if not pid_str.isdigit():
                continue
            pid = int(pid_str)
            if pid != os.getpid() and pid > 1:
                subprocess.run(['kill', '-9', str(pid)], timeout=5)
                logger.info(f"🔪 Killed PID {pid} on port {port}")
        time.sleep(0.5)
        logger.info(f"✅ Port {port} freed.")
        return True
    except FileNotFoundError:
        logger.debug("fuser not available, assuming port is free")
        return True
    except Exception as e:
        logger.debug(f"_free_port_linux error: {e}")
        return True
