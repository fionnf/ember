#!/usr/bin/env python3
"""Generate fl11.kicad_sch from the routed board.

Nets are read out of fl11.kicad_pcb rather than typed again, so the schematic
cannot drift from the layout. Connectivity is expressed with global labels on
every pin - electrically identical to drawn wires, and legible on one sheet.

Usage:  <kicad-python> gen_schematic.py fl11.kicad_pcb fl11.kicad_sch <Espressif.kicad_sym>
"""
import sys, os, re, hashlib
import pcbnew

PCB, OUT, ESPSYM = sys.argv[1], sys.argv[2], sys.argv[3]
LIBDIR = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/symbols")

LIB_OF = {
    "R": "Device:R", "C": "Device:C", "F": "Device:Fuse", "LD": "LED:SK6812",
    "Q": "Transistor_FET:AO3401A", "SW": "Switch:SW_Push",
    "TP": "Connector:TestPoint", "J2": "Connector:TestPoint",
    "J3": "Connector:TestPoint", "J4": "Connector:TestPoint",
}
EXACT = {
    "U1": "Espressif:ESP32-C3-MINI-1", "U2": "74xGxx:74AHCT1G125",
    "U3": "Regulator_Linear:AP2112K-3.3", "U4": "Power_Protection:USBLC6-2SC6",
    "J1": "Connector:USB_C_Receptacle", "C1": "Device:C_Polarized",
}

def uid(*parts):
    h = hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def symbol_block(lib, name):
    """Pull one symbol's full s-expression out of a .kicad_sym by brace depth."""
    path = ESPSYM if lib == "Espressif" else f"{LIBDIR}/{lib}.kicad_sym"
    lines = open(path).read().split("\n")
    start = next((i for i, l in enumerate(lines) if l.strip() == f'(symbol "{name}"'), None)
    if start is None: raise SystemExit(f"symbol {lib}:{name} not found")
    depth = 0
    for i in range(start, len(lines)):
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0 and i > start:
            return "\n".join(lines[start:i+1])
    raise SystemExit(f"unterminated {lib}:{name}")

def pins_of(block):
    out = []
    for chunk in block.split("(pin ")[1:]:
        m = re.search(r'\(at ([-\d.]+) ([-\d.]+) ([\d.]+)\)', chunk)
        n = re.search(r'\(number "([^"]+)"', chunk)
        if m and n:
            out.append((n.group(1), float(m.group(1)), float(m.group(2)), float(m.group(3))))
    seen, uniq = set(), []
    for p in out:
        if p[0] not in seen: seen.add(p[0]); uniq.append(p)
    return uniq

# ── Read refs, values and per-pad nets from the board
board = pcbnew.LoadBoard(PCB)
parts = []
for fp in board.Footprints():
    ref = fp.GetReference()
    if ref.startswith("H"): continue                    # mounting holes carry no net
    base = re.match(r"([A-Za-z]+)", ref).group(1)
    lib_id = EXACT.get(ref) or LIB_OF.get(ref.split("_")[0]) or LIB_OF.get(base)
    if not lib_id: continue
    nets = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
    parts.append((ref, fp.GetValue(), lib_id, nets))
parts.sort(key=lambda r: (re.match(r"([A-Za-z]+)", r[0]).group(1),
                          int(re.sub(r"\D", "", r[0]) or 0)))

cache = {}
def get(lib_id):
    if lib_id not in cache:
        lib, name = lib_id.split(":")
        blk = symbol_block(lib, name)
        cache[lib_id] = (blk, pins_of(blk))
    return cache[lib_id]

lib_syms, body = [], []
for lib_id in sorted({p[2] for p in parts}):
    blk, _ = get(lib_id)
    lib, name = lib_id.split(":")
    lib_syms.append(re.sub(r'^\(symbol "%s"' % re.escape(name),
                           '(symbol "%s"' % lib_id, blk, count=1))

# ── Place on a grid; big parts get their own column
# Everything must land on the 1.27 mm schematic grid or labels will not attach to pins.
X0, Y0, DX, DY = 25.4, 25.4, 63.5, 44.45
col = row = 0
for ref, val, lib_id, nets in parts:
    blk, pins = get(lib_id)
    if len(pins) > 12 and row != 0:
        col += 1; row = 0
    sx, sy = X0 + col*DX, Y0 + row*DY
    u = uid(ref)
    body.append(f'''  (symbol (lib_id "{lib_id}") (at {sx} {sy} 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) (uuid "{u}")
    (property "Reference" "{ref}" (at {sx+6.5} {sy-6.5} 0)
      (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "{val}" (at {sx+6.5} {sy-4.0} 0)
      (effects (font (size 1.27 1.27)) (justify left)))
    (instances (project "fl11" (path "/{uid("sheet")}" (reference "{ref}") (unit 1))))
  )''')
    for num, px, py, ang in pins:
        net = nets.get(num, "")
        if not net or net.startswith("unconnected") or net.startswith("Net-"): continue
        # library Y is up-positive, schematic Y is down-positive
        cx, cy = sx + px, sy - py
        rad = (ang + 180) % 360
        dx = round({0: 1, 90: 0, 180: -1, 270: 0}.get(rad, 1), 3)
        dy = round({0: 0, 90: -1, 180: 0, 270: 1}.get(rad, 0), 3)
        ex, ey = cx + dx*3.81, cy + dy*3.81
        body.append(f'''  (wire (pts (xy {cx} {cy}) (xy {ex} {ey}))
    (stroke (width 0) (type default)) (uuid "{uid(ref,num,"w")}"))
  (global_label "{net}" (shape passive) (at {ex} {ey} {0 if dx>=0 else 180})
    (effects (font (size 1.27 1.27)) (justify {"left" if dx>=0 else "right"}))
    (uuid "{uid(ref,num,"l")}"))''')
    row += 1
    if row * DY > 260: col += 1; row = 0

with open(OUT, "w") as f:
    f.write(f'''(kicad_sch (version 20231120) (generator "fl11_gen") (uuid "{uid("sch")}")
  (paper "A2")
  (title_block
    (title "FL-11 - Linked Friend Lights")
    (date "2026-08-20")
    (rev "G")
    (company "(c) 2026 Fionn Ferreira - github.com/fionnf/linked-friend-lights-public")
  )
  (lib_symbols
{chr(10).join(lib_syms)}
  )
{chr(10).join(body)}
)
''')
print(f"{len(parts)} symbols, {len(lib_syms)} unique, nets read from the board")
