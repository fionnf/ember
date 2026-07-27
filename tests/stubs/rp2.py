class PIO: OUT_LOW = 0; SHIFT_LEFT = 1
def asm_pio(**kw):
    def deco(fn): return fn      # never executes the PIO body
    return deco
class StateMachine:
    def __init__(self, *a, **k): self.words = []
    def active(self, v): pass
    def put(self, buf, shift=0): self.words.append(len(buf))
