#!/usr/bin/env python3
"""
Firmware smoke test — actually RUNS main() against stubbed MicroPython
modules. `python -m py_compile` cannot catch runtime errors: a stray
function-level `import machine` once shadowed the module-level import for
the whole of main(), so arming the watchdog raised UnboundLocalError and
every board boot-looped. Only executing main() catches that class of bug.

Run from the repo root:   python3 tests/test_firmware.py
"""
import os, sys, json, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def run():
    work = tempfile.mkdtemp(prefix="fwtest-")
    for f in ("main.py", "colour.py", "sk6812.py", "touch.py"):
        shutil.copy(os.path.join(ROOT, f), work)
    for item in os.listdir(os.path.join(HERE, "stubs")):
        src = os.path.join(HERE, "stubs", item)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(
            src, os.path.join(work, item))

    sys.path.insert(0, work)
    os.chdir(work)                      # state.json etc. land in the sandbox
    for m in list(sys.modules):
        if m.split(".")[0] in ("machine","utime","network","rp2","webrepl",
                               "ntptime","urandom","ujson","umqtt","config",
                               "main","colour","sk6812","touch"):
            del sys.modules[m]

    # gc.mem_free() is MicroPython-only; gc is a builtin so it cannot be
    # shadowed by a stub file — patch the attribute instead.
    import gc
    if not hasattr(gc, "mem_free"): gc.mem_free = lambda: 102400
    # sys.print_exception is MicroPython-only
    import traceback as _tb
    if not hasattr(sys, "print_exception"):
        sys.print_exception = lambda e, *a: _tb.print_exception(type(e), e, e.__traceback__)

    import machine, utime, umqtt.simple as us
    import main as fw

    failures = []
    def check(name, cond, detail=""):
        print(("  PASS  " if cond else "  FAIL  ") + name + (f"  {detail}" if detail and not cond else ""))
        if not cond: failures.append(name)

    # Stop the infinite main loop after N iterations by making the frame
    # sleep raise once we've seen enough of the loop.
    class Done(Exception): pass
    iters = [0]
    real_sleep_ms = utime.sleep_ms
    def counting_sleep(ms):
        real_sleep_ms(ms)
        iters[0] += 1
        if iters[0] > LIMIT: raise Done()
    utime.sleep_ms = counting_sleep
    fw.utime.sleep_ms = counting_sleep

    print("\n=== 1. boot + main loop ===")
    LIMIT = 3000                        # ~3 s of simulated loop
    try:
        fw.main()
        check("main() ran without crashing", False, "returned unexpectedly")
    except Done:
        check("main() boots and runs the loop (no UnboundLocalError)", True)
    except machine.ResetCalled:
        check("main() booted without an unexpected reset", False)
    except Exception as e:
        check(f"main() boots cleanly", False, f"{type(e).__name__}: {e}")
        import traceback; traceback.print_exc()

    check("hardware watchdog armed", fw.wdt is not None)
    check("watchdog is being fed", fw.wdt and fw.wdt.feeds > 10,
          f"feeds={fw.wdt.feeds if fw.wdt else 0}")
    check("MQTT client connected", fw.client is not None)

    subs = [s.decode() for s in fw.client.subs]
    check("subscribed to events topic", "test_prefix/events" in subs, str(subs))
    check("subscribed to RETAINED ALARMS topic", "test_prefix/alarms" in subs, str(subs))
    check("Last-Will registered", fw.client.will is not None)

    def _s(x): return x.decode() if isinstance(x, bytes) else x
    topics = [_s(t) for t, m, r in us.published]
    check("published retained presence", any("status/board_a" in t for t in topics))
    hb = [json.loads(_s(m)) for t, m, r in us.published if "heartbeat" in _s(m)]
    check("published a heartbeat", len(hb) > 0)
    if hb:
        check("heartbeat reports ntp + alarms", "ntp" in hb[0] and "alarms" in hb[0], str(hb[0]))

    print("\n=== 2. reboot command (the button) ===")
    us.published.clear()
    fw.client.inject(b"test_prefix/events",
                     json.dumps({"from": "web_app", "reboot": True}).encode())
    before = machine.reset_count[0]
    try:
        fw.client.check_msg()
    except machine.ResetCalled:
        pass
    check("reboot message triggers machine.reset()", machine.reset_count[0] == before + 1)
    check("state saved before rebooting", os.path.exists(os.path.join(work, "state.json")))

    print("\n=== 3. retained alarm schedule ===")
    fw.client.inject(b"test_prefix/alarms",
                     json.dumps([{"enabled": True, "type": "sunrise", "hour": 5,
                                  "minute": 0, "days": [0,1,2,3,4],
                                  "boards": ["board_a","board_b"]}]).encode())
    fw.client.check_msg()
    check("retained array installs the schedule", len(fw._alarms) == 1, str(fw._alarms))

    print("\n=== 4. hostile input cannot crash the handler ===")
    ok = True
    for bad in [b"not json", b"null", b"[1,2,3]", b'{"groups":"x"}',
                b'{"brightness":"NaN"}', b'{"set_alarms":42}', b"\xff\xfe", b"{}"]:
        try:
            fw.client.inject(b"test_prefix/events", bad); fw.client.check_msg()
        except machine.ResetCalled:
            pass
        except Exception as e:
            ok = False; print(f"    raised on {bad!r}: {type(e).__name__}: {e}")
    check("malformed messages never raise", ok)

    print("\n=== 5. commands apply ===")
    fw.client.inject(b"test_prefix/events", json.dumps({
        "from": "web_app", "on": True, "brightness": 0.42, "fade_steps": 120,
        "groups": [{"pos": 0.5, "w": 0.5, "size": 4},
                   {"pos": 0.9, "w": 0.1, "size": 6}]}).encode())
    fw.client.check_msg()
    check("brightness applied", abs(fw.engine._brightness - 0.42) < 1e-6,
          str(fw.engine._brightness))
    check("fade_steps applied", fw.engine._fade_steps == 120, str(fw.engine._fade_steps))
    check("groups cover the whole strip", sum(fw.engine._group_sizes) == 10,
          str(fw.engine._group_sizes))

    print("\n=== 6. test_alarm ===")
    fw._test_alarm = None
    fw.client.inject(b"test_prefix/events", json.dumps({
        "from": "web_app", "test_alarm": "sunrise", "test_seconds": 20}).encode())
    fw.client.check_msg()
    check("test_alarm queued for the main loop", fw._test_alarm is not None,
          str(fw._test_alarm))

    shutil.rmtree(work, ignore_errors=True)
    print()
    if failures:
        print(f"FAILED ({len(failures)}): " + ", ".join(failures)); return 1
    print("ALL FIRMWARE SMOKE TESTS PASSED"); return 0

if __name__ == "__main__":
    sys.exit(run())
