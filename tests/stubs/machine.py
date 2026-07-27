"""Minimal MicroPython `machine` stub."""
class ResetCalled(BaseException):
    """Reset never returns on real hardware, so this must bypass
    `except Exception` handlers the way a real reset does."""
reset_count = [0]
class Pin:
    OUT = 0; IN = 1
    def __init__(self, num, mode=OUT): self.num = num; self._v = 0
    def init(self, mode): pass
    def value(self, v=None):
        if v is None: return 0          # reads low → touch never triggers
        self._v = v
class WDT:
    def __init__(self, timeout=0): self.timeout = timeout; self.feeds = 0
    def feed(self): self.feeds += 1
def unique_id(): return b"\xde\xad\xbe\xef"
def reset():
    reset_count[0] += 1
    raise ResetCalled()
