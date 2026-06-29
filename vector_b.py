import importlib
import time

N = 10000

start = time.perf_counter_ns()
for _ in range(N):
    importlib.import_module("babylon60.crypto")
direct_ns = time.perf_counter_ns() - start

start = time.perf_counter_ns()
for _ in range(N):
    importlib.import_module("cortex.crypto")
proxy_ns = time.perf_counter_ns() - start

print({
    "direct_per_import_ns": direct_ns / N,
    "proxy_per_import_ns": proxy_ns / N,
    "overhead_ns": (proxy_ns - direct_ns) / N,
})
