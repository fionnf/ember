# ============================================================
#  boot.py — OTA updater
#  Runs before main.py. Downloads latest code from GitHub,
#  then MicroPython continues to main.py automatically.
#  config.py is never touched — it stays per-board.
# ============================================================

import machine
import network
import utime

# ── Files to sync from GitHub ────────────────────────────────
# Point this at YOUR fork. Boards pull firmware from here on every daily
# reboot, so whoever controls this repo controls the lamps.
REPO_RAW = "https://raw.githubusercontent.com/fionnf/ember/master/"
SYNC_FILES = ["main.py", "colour.py", "sk6812.py", "touch.py"]

# ── Crash-loop rollback ──────────────────────────────────────
# The compile gate below rejects firmware that doesn't parse, but code can
# be perfectly valid and still fail at runtime — a stray function-level
# import once shadowed a module-level one and every board boot-looped,
# unreachable until a human pushed a fix.
#
# So: count boots that never reach stability. main.py clears the counter
# after it has run for a minute and promotes the running files to `.ok`
# backups. After MAX_FAILS unstable boots we restore those backups and skip
# the update for one boot, which brings the lamp back on its own.
#
# No record is kept of the rejected version: the next scheduled reboot
# re-downloads master, so a pushed fix is picked up with no stale state to
# clear, and a few quick power cycles can't pin a board to old firmware.
FAIL_FILE     = "bootfail.txt"
ROLLBACK_FLAG = "rolledback.txt"
OK_SUFFIX     = ".ok"
MAX_FAILS     = 3

def _read_fails():
    try:
        with open(FAIL_FILE) as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0

def _write_fails(n):
    try:
        with open(FAIL_FILE, "w") as f:
            f.write(str(n))
    except Exception:
        pass

def _have_backups():
    for fname in SYNC_FILES:
        try:
            open(fname + OK_SUFFIX).close()
        except OSError:
            return False
    return True

def _rollback():
    """Restore the last firmware set that proved itself stable."""
    import os
    for fname in SYNC_FILES:
        try:
            with open(fname + OK_SUFFIX) as src:
                data = src.read()
            tmp = fname + ".new"
            with open(tmp, "w") as dst:
                dst.write(data)
            os.rename(tmp, fname)
            print(f"[ota] rolled back {fname}")
        except Exception as e:
            print(f"[ota] could not roll back {fname}: {e}")
    try:
        with open(ROLLBACK_FLAG, "w") as f:
            f.write("1")     # main.py reports this so the failure is visible
    except Exception:
        pass

def _check_crash_loop():
    """Returns True if firmware was rolled back (skip the update this boot)."""
    # A power cycle is not a crash — only soft/watchdog resets accumulate.
    fresh_power_on = False
    try:
        if machine.reset_cause() == machine.PWRON_RESET:
            fresh_power_on = True
    except Exception:
        pass          # not all ports expose reset_cause; assume it counts

    fails = 0 if fresh_power_on else _read_fails() + 1
    _write_fails(fails)
    if fails >= MAX_FAILS and _have_backups():
        print(f"[ota] {fails} boots without reaching stability — "
              "restoring last known-good firmware")
        _rollback()
        _write_fails(0)
        return True
    if fails > 1:
        print(f"[ota] warning: {fails} consecutive unstable boots")
    return False

# ── Connect WiFi (mirrors main.py logic, standalone) ─────────
def _load_networks():
    try:
        from config import WIFI_NETWORKS
    except Exception:
        WIFI_NETWORKS = []
    extra = []
    try:
        import ujson
        with open("networks.json") as f:
            extra = ujson.load(f)
    except Exception:
        pass
    return WIFI_NETWORKS + extra

def _connect():
    networks = _load_networks()
    if not networks:
        print("[ota] no networks configured — skipping update")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True

    try:
        visible = {ap[0].decode("utf-8", "ignore") for ap in wlan.scan()}
    except Exception:
        visible = set()

    for ssid, password in networks:
        if visible and ssid not in visible:
            continue
        print(f"[ota] connecting to {ssid}...")
        wlan.connect(ssid, password)
        deadline = utime.ticks_add(utime.ticks_ms(), 12_000)
        while not wlan.isconnected():
            if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
                wlan.disconnect()
                utime.sleep_ms(300)
                break
            utime.sleep_ms(200)
        if wlan.isconnected():
            print(f"[ota] connected — IP {wlan.ifconfig()[0]}")
            return True

    print("[ota] no WiFi — skipping update, booting with existing files")
    return False


def _update():
    try:
        import urequests
    except ImportError:
        print("[ota] urequests not available — skipping update")
        return
    import os

    # Clear anything a previous interrupted run left behind
    for fname in SYNC_FILES:
        try:
            os.remove(fname + ".new")
        except OSError:
            pass

    # ── Phase 1: download and verify EVERY file before installing any ──
    # Installing file-by-file meant a mid-update network drop could leave
    # a new main.py running against an old colour.py. The firmware files
    # are versioned together, so they must be installed together.
    staged = []
    ok = True
    for fname in SYNC_FILES:
        try:
            r = urequests.get(REPO_RAW + fname, timeout=10)
            if r.status_code != 200:
                print(f"[ota] {fname} — HTTP {r.status_code}, aborting update")
                r.close()
                ok = False
                break
            content = r.text
            r.close()
        except Exception as e:
            print(f"[ota] {fname} download failed: {e}, aborting update")
            ok = False
            break

        # Refuse anything that doesn't compile — a bad push to master, a
        # truncated download or an HTML error page must never brick a board.
        try:
            compile(content, fname, "exec")
        except Exception as e:
            print(f"[ota] {fname} failed syntax check, aborting update ({e})")
            ok = False
            break

        try:
            with open(fname, "r") as f:
                if f.read() == content:
                    continue            # already current, nothing to stage
        except OSError:
            pass                        # file doesn't exist yet

        try:
            with open(fname + ".new", "w") as f:
                f.write(content)
            staged.append(fname)
        except Exception as e:
            print(f"[ota] {fname} could not be staged: {e}, aborting update")
            ok = False
            break

    # ── Phase 2: commit, or discard the whole set ──
    if not ok:
        for fname in staged:
            try:
                os.remove(fname + ".new")
            except OSError:
                pass
        print("[ota] update abandoned — running existing firmware")
        return

    if not staged:
        print("[ota] all files up to date")
        return

    for fname in staged:
        os.rename(fname + ".new", fname)   # rename is atomic
        print(f"[ota] updated {fname}")
    print(f"[ota] installed: {staged}")


# ── Run ───────────────────────────────────────────────────────
# Rolled back? Boot the restored firmware without re-fetching master, or we
# would immediately reinstall the version that was just failing.
if _check_crash_loop():
    print("[ota] booting restored firmware (update skipped this boot)")
else:
    print("[ota] checking for updates...")
    if _connect():
        _update()
    print("[ota] booting...")
