_now = [0]
def ticks_ms(): return _now[0]
def ticks_diff(a, b): return a - b
def ticks_add(a, b): return a + b
def time(): return _now[0] // 1000
def sleep_ms(ms): _now[0] += ms
def sleep_us(us): _now[0] += max(1, us // 1000)
def sleep(s): _now[0] += int(s * 1000)
def localtime(): 
    s = _now[0] // 1000
    return (2026, 7, 27, (s // 3600) % 24, (s // 60) % 60, s % 60, 0, 208)
def advance(ms): _now[0] += ms
