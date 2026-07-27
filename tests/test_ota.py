#!/usr/bin/env python3
"""
OTA tests — boot.py installs firmware as an all-or-nothing set.

Installing file-by-file meant a mid-update network drop could leave a new
main.py running against an old colour.py. Firmware files are versioned
together, so they must land together.

Run from the repo root:   python3 tests/test_ota.py
"""
import os, re, sys, shutil, tempfile, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["main.py", "colour.py", "sk6812.py", "touch.py"]

def load_update_fn(responses):
    """Exec boot.py's _update() with a stubbed urequests."""
    src = open(os.path.join(ROOT, "boot.py")).read()
    body = src[src.index("def _update():"):src.index("# ── Run ─")]

    class Resp:
        def __init__(self, text, code=200): self.text, self.status_code = text, code
        def close(self): pass

    calls = []
    def get(url, timeout=None):
        name = url.rsplit("/", 1)[-1]
        calls.append(name)
        r = responses[name]
        if isinstance(r, Exception): raise r
        return Resp(*r) if isinstance(r, tuple) else Resp(r)

    ns = {"SYNC_FILES": FILES, "REPO_RAW": "https://example/",
          "print": lambda *a, **k: None}
    sys.modules["urequests"] = types.SimpleNamespace(get=get)
    exec(body, ns)
    return ns["_update"], calls

def sandbox(old="OLD"):
    d = tempfile.mkdtemp(prefix="ota-")
    for f in FILES:
        open(os.path.join(d, f), "w").write(f"# {old} {f}\n")
    return d

def contents(d):
    return {f: open(os.path.join(d, f)).read().strip() for f in FILES}

def leftovers(d):
    return [f for f in os.listdir(d) if f.endswith(".new") or f.endswith(".tmp")]

fails = []
def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  {detail}" if detail and not cond else ""))
    if not cond: fails.append(name)

print("\n=== 1. happy path: all files update together ===")
d = sandbox(); os.chdir(d)
upd, _ = load_update_fn({f: f"# NEW {f}\n" for f in FILES})
upd()
c = contents(d)
check("every file updated", all(v.startswith("# NEW") for v in c.values()), str(c))
check("no temp files left", not leftovers(d), str(leftovers(d)))

print("\n=== 2. network drop mid-update → NOTHING installs ===")
d = sandbox(); os.chdir(d)
upd, _ = load_update_fn({"main.py": "# NEW main.py\n",
                         "colour.py": OSError("connection reset"),
                         "sk6812.py": "# NEW sk6812.py\n",
                         "touch.py": "# NEW touch.py\n"})
upd()
c = contents(d)
check("no mixed-version firmware", all(v.startswith("# OLD") for v in c.values()), str(c))
check("staged files cleaned up", not leftovers(d), str(leftovers(d)))

print("\n=== 3. one file fails to compile → NOTHING installs ===")
d = sandbox(); os.chdir(d)
upd, _ = load_update_fn({"main.py": "# NEW main.py\n",
                         "colour.py": "def broken( syntax error\n",
                         "sk6812.py": "# NEW sk6812.py\n",
                         "touch.py": "# NEW touch.py\n"})
upd()
c = contents(d)
check("syntax error blocks the whole set", all(v.startswith("# OLD") for v in c.values()), str(c))

print("\n=== 4. HTTP error (e.g. GitHub 500 / HTML page) → NOTHING installs ===")
d = sandbox(); os.chdir(d)
upd, _ = load_update_fn({"main.py": "# NEW main.py\n",
                         "colour.py": ("<html>500</html>", 500),
                         "sk6812.py": "# NEW sk6812.py\n",
                         "touch.py": "# NEW touch.py\n"})
upd()
check("HTTP failure blocks the set", all(v.startswith("# OLD") for v in contents(d).values()))

print("\n=== 5. unchanged files are not rewritten ===")
d = sandbox(); os.chdir(d)
upd, _ = load_update_fn({f: f"# OLD {f}\n" for f in FILES})
before = {f: os.stat(os.path.join(d, f)).st_mtime_ns for f in FILES}
upd()
after = {f: os.stat(os.path.join(d, f)).st_mtime_ns for f in FILES}
check("no needless flash writes", before == after)

print("\n=== 6. stale .new from an interrupted run is cleaned ===")
d = sandbox(); os.chdir(d)
open(os.path.join(d, "main.py.new"), "w").write("# JUNK\n")
upd, _ = load_update_fn({f: f"# OLD {f}\n" for f in FILES})
upd()
check("stale staging file removed", "main.py.new" not in os.listdir(d), str(os.listdir(d)))

os.chdir(ROOT)
print()
if fails:
    print(f"FAILED ({len(fails)}): " + ", ".join(fails)); sys.exit(1)
print("ALL OTA TESTS PASSED")
