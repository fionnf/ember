# ============================================================
#  boot.py — OTA updater
#  Runs before main.py. Downloads latest code from GitHub,
#  then MicroPython continues to main.py automatically.
#  config.py is never touched — it stays per-board.
# ============================================================

import network
import utime

# ── Files to sync from GitHub ────────────────────────────────
REPO_RAW = "https://raw.githubusercontent.com/fionnf/linked_friend_lights/master/"
SYNC_FILES = ["main.py", "colour.py", "sk6812.py", "touch.py"]

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
print("[ota] checking for updates...")
if _connect():
    _update()
print("[ota] booting...")
