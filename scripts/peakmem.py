"""Run a command; print its wall time and the peak memory of its whole process tree."""
import subprocess
import sys
import time

import psutil

start = time.perf_counter()
proc = subprocess.Popen(sys.argv[1:])
root, peak = psutil.Process(proc.pid), 0
while proc.poll() is None:
    try:
        tree = [root, *root.children(recursive=True)]
        peak = max(peak, sum(p.memory_info().rss for p in tree if p.is_running()))
    except psutil.Error:
        pass
    time.sleep(0.2)
print(f"exit={proc.returncode} seconds={time.perf_counter() - start:.1f} peak_rss_mb={peak / 2**20:.0f}", flush=True)
