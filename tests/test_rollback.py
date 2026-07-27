#!/usr/bin/env python3
"""
Crash-loop rollback tests.

The compile gate rejects firmware that doesn't parse, but valid code can
still fail at runtime — a stray function-level import once shadowed a
module-level one and every board boot-looped, unreachable until a human
pushed a fix. boot.py now counts boots that never reach stability and
restores the last firmware that main.py declared good.

Run from the repo root:   python3 tests/test_rollback.py
"""
import os, sys, types, shutil, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["main.py", "colour.py", "sk6812.py", "touch.py"]

fails = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  {detail}" if detail and not cond else ""))
    if not cond: fails.append(name)

def load_boot(reset_cause="SOFT"):
    """Exec boot.py's rollback helpers with a stubbed `machine`."""
    src = open(os.path.join(ROOT, "boot.py")).read()
    body = src[src.index("FAIL_FILE     ="):src.index("def _load_networks")]
    m = types.SimpleNamespace(PWRON_RESET=1, SOFT_RESET=3,
                              reset_cause=lambda: 1 if reset_cause == "PWRON" else 3)
    ns = {"SYNC_FILES": FILES, "machine": m, "print": lambda *a, **k: None}
    exec(body, ns)
    return ns

def load_main_stable():
    """Exec main.py's mark_stable() with real os."""
    src = open(os.path.join(ROOT, "main.py")).read()
    body = src[src.index("STABLE_MS     ="):src.index("def connect_wifi")]
    ns = {"os": os, "print": lambda *a, **k: None}
    exec(body, ns)
    return ns

def sandbox(version="GOOD"):
    d = tempfile.mkdtemp(prefix="rb-")
    for f in FILES:
        open(os.path.join(d, f), "w").write(f"# {version} {f}\n")
    return d

def ver(d, f="main.py"):
    return open(os.path.join(d, f)).read().split()[1]

print("\n=== 1. a stable boot creates known-good backups ===")
d = sandbox("GOOD"); os.chdir(d)
mainns = load_main_stable()
mainns["mark_stable"]()
check("backups written", all(os.path.exists(os.path.join(d, f + ".ok")) for f in FILES))
check("fail counter cleared", open(os.path.join(d, "bootfail.txt")).read() == "0")

print("\n=== 2. bad firmware arrives, then crash-loops → rolled back ===")
for f in FILES:                                   # simulate an OTA to BAD
    open(os.path.join(d, f), "w").write(f"# BAD {f}\n")
check("running BAD before any reboot", ver(d) == "BAD")

boot = load_boot("SOFT")
rolled = [boot["_check_crash_loop"]() for _ in range(3)]
check("no rollback on the first two crashes", rolled[:2] == [False, False], str(rolled))
check("rolled back on the third", rolled[2] is True, str(rolled))
check("running the known-good firmware again", ver(d) == "GOOD", ver(d))
check("all four files restored together",
      all(ver(d, f) == "GOOD" for f in FILES))
check("rollback flag set for reporting", os.path.exists(os.path.join(d, ROLLBACK := "rolledback.txt")))
check("counter reset after rollback", open(os.path.join(d, "bootfail.txt")).read() == "0")

print("\n=== 3. main.py clears the flag once stable again ===")
mainns["mark_stable"]()
check("rollback flag cleared", not os.path.exists(os.path.join(d, "rolledback.txt")))
check("backups still GOOD", open(os.path.join(d, "main.py.ok")).read().split()[1] == "GOOD")

print("\n=== 4. power cycles are NOT treated as crashes ===")
d = sandbox("GOOD"); os.chdir(d)
load_main_stable()["mark_stable"]()
for f in FILES:
    open(os.path.join(d, f), "w").write(f"# NEW {f}\n")
boot = load_boot("PWRON")
rolled = [boot["_check_crash_loop"]() for _ in range(5)]
check("5 power-ons never trigger a rollback", not any(rolled), str(rolled))
check("new firmware left alone", ver(d) == "NEW", ver(d))

print("\n=== 5. no backups yet → nothing to roll back to, no crash ===")
d = sandbox("ONLY"); os.chdir(d)
boot = load_boot("SOFT")
rolled = [boot["_check_crash_loop"]() for _ in range(5)]
check("never claims to have rolled back", not any(rolled), str(rolled))
check("firmware untouched", ver(d) == "ONLY")

print("\n=== 6. a stable run resets the counter, so scattered crashes never trip it ===")
d = sandbox("GOOD"); os.chdir(d)
mainns = load_main_stable(); mainns["mark_stable"]()
boot = load_boot("SOFT")
tripped = False
for _ in range(10):                # crash, recover, crash, recover ...
    if boot["_check_crash_loop"](): tripped = True
    mainns["mark_stable"]()        # each boot reached stability
check("isolated crashes don't accumulate", not tripped)

os.chdir(ROOT)
print()
if fails:
    print(f"FAILED ({len(fails)}): " + ", ".join(fails)); sys.exit(1)
print("ALL ROLLBACK TESTS PASSED")
