# FL-11 rev B pours and routing.
import sys, pcbnew
from pcbnew import VECTOR2I, FromMM as MM
NLED = 15                     # must match build_fl11.py
B = sys.argv[1]
board = pcbnew.LoadBoard(B)
nets = board.GetNetsByName()
def N(n): return nets[n]
KEEP = []   # SetOutline does not take ownership; a GC'd SHAPE_POLY_SET segfaults on save

def zone(layer, net, pts, prio=0, solid=False):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(N(net))
    z.SetAssignedPriority(prio); z.SetIsFilled(False)
    poly = pcbnew.SHAPE_POLY_SET(); poly.NewOutline()
    for x,y in pts: poly.Append(MM(x), MM(y))
    z.SetOutline(poly); KEEP.append(poly)
    z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.25)); z.SetThermalReliefSpokeWidth(MM(0.4))
    board.Add(z); return z

def rect(layer, net, x1,y1,x2,y2, prio=0, solid=False):
    return zone(layer, net, [(x1,y1),(x2,y1),(x2,y2),(x1,y2)], prio, solid)

def track(x1,y1,x2,y2,net,w=0.25,layer=pcbnew.F_Cu):
    t=pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(MM(x1),MM(y1)))
    t.SetEnd(VECTOR2I(MM(x2),MM(y2))); t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(N(net))
    board.Add(t); return t

def via(x,y,net):
    v=pcbnew.PCB_VIA(board); v.SetPosition(VECTOR2I(MM(x),MM(y)))
    v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(N(net)); board.Add(v); return v

# ── Strip cross-section (GND at the y=0 side, 5 V under the LED anodes)
rect(pcbnew.F_Cu, "GND",    0.4, 0.40, 186.6, 9.30, prio=1)
rect(pcbnew.F_Cu, "LED_5V", 0.4, 12.40, 186.6, 17.00, prio=1)
# Bottom plane over strip + bulge. NOT under the pad tab (PAD_BACK_KO).
zone(pcbnew.B_Cu, "GND", [(0.4,0.4),(186.6,0.4),(186.6,19.6),(129.6,19.6),
                          (129.6,51.6),(66.4,51.6),(66.4,19.6),(0.4,19.6)], prio=0, solid=True)
# Bulge: GND everywhere, with a 5 V island that reaches up into the strip pour to merge.
rect(pcbnew.F_Cu, "GND",    66.4, 20.0, 129.6, 51.6, prio=0)
# U1's thermal pad wants a solid tie; the rest of the bulge keeps thermal relief so the
# 0402s do not tombstone (§7.7).
rect(pcbnew.F_Cu, "GND", 91.0, 29.0, 105.0, 47.0, prio=3, solid=True)
# J1's shield pads are large PTH; give them a solid tie too, without removing thermal
# relief from the 0402s elsewhere in the bulge.
rect(pcbnew.F_Cu, "GND", 74.0, 42.0, 88.5, 51.6, prio=3, solid=True)
# prio 2 so the overlap with the strip pour resolves instead of reading as an intersect
rect(pcbnew.F_Cu, "LED_5V", 84.0, 16.5, 97.0, 29.5, prio=2)
# Touch pad, on the snap-off section. Electrodes 17 x 12 = 204 mm2 each, guard ring
# on the far edge, no copper on B.Cu beneath either.
# Interdigitated electrodes. Two solid plates couple mostly through the plastic's
# thickness; a comb pushes the field OUT of the surface as fringing, which is what a
# finger behind an overlay actually intercepts. Finger pitch 3.0 mm means a ~10 mm
# fingertip always spans several SENSE/GND pairs, so the delta stays large through a
# thin cover and degrades gracefully as the overlay thickens.
# Interdigitated electrodes. Two solid plates couple mostly through the overlay's
# thickness; a comb pushes the field OUT of the surface as fringing, which is what a
# finger behind plastic actually intercepts. Pitch 3.0 mm with 1.1 mm fingers means a
# ~10 mm fingertip always spans several SENSE/GND pairs.
#
# Each electrode is ONE polygon. Built as overlapping rectangles they filled as separate
# zones and the priority clipping severed every GND finger from its spine - eight
# isolated islands and a dead half of the sensor.
FP, FH, NF = 3.0, 1.1, 7
SX, SW, SXF = 136.0, 1.2, 150.6      # SENSE spine x, width, finger tip
GX, GW, GXF = 153.0, 1.2, 138.4      # GND spine x (right), width, finger tip
TOP, SBOT   = 29.0, 47.0
BAR_T, BAR_B = 47.6, 48.8            # GND return bar, brings GND back to the break edge

pts = [(SX, TOP), (SX+SW, TOP)]
for k in range(NF):
    ft = 29.6 + FP*k
    pts += [(SX+SW, ft), (SXF, ft), (SXF, ft+FH), (SX+SW, ft+FH)]
pts += [(SX+SW, SBOT), (SX, SBOT)]
zone(pcbnew.F_Cu, "TOUCH_SENSE", pts, prio=1, solid=True)

pts = [(GX, TOP), (GX-GW, TOP)]
for k in range(NF):
    ft = 31.1 + FP*k
    pts += [(GX-GW, ft), (GXF, ft), (GXF, ft+FH), (GX-GW, ft+FH)]
pts += [(GX-GW, BAR_T), (SX, BAR_T), (SX, BAR_B), (GX, BAR_B)]
zone(pcbnew.F_Cu, "GND", pts, prio=1, solid=True)   # solid: nothing to tombstone on the pad section

def pad(ref, num):
    fp = board.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber()==num:
            v=p.GetPosition(); return v.x/1e6, v.y/1e6
    raise SystemExit(f"no pad {ref}.{num}")

routed = 0
CH = 11.0
for i in range(1, NLED):
    x1,y1 = pad(f"LD{i}","2"); x2,y2 = pad(f"LD{i+1}","4"); net=f"D_{i}_{i+1}"
    track(x1,y1,x1,CH,net); track(x1,CH,x2,CH,net); track(x2,CH,x2,y2,net); routed += 3
# Buffer output leaves the bulge and runs ~80 mm to LD1. Past the ~75 mm critical
# length, so R11 is now a 100R series termination (AHCT Zout 15-25R + ~120R trace).
# LED_DATA_5V left to the autorouter: a direct U2.4 -> R11.1 line clips U2.5.
# DIN must NOT share the y=11 data channel - it would cross every hop. It runs
# below the 5 V pour at y=18.6, then climbs at x=4.0, clear of LD1's body.
x,y = pad("R11","2"); dx,dy = pad("LD1","4")
DIN_Y, DIN_X, EXIT = 18.6, 4.0, 89.0
track(x,y, EXIT,y, "LED_DIN1"); track(EXIT,y, EXIT,DIN_Y, "LED_DIN1")
track(EXIT,DIN_Y, DIN_X,DIN_Y, "LED_DIN1"); track(DIN_X,DIN_Y, DIN_X,dy, "LED_DIN1")
track(DIN_X,dy, dx,dy, "LED_DIN1"); routed += 5
x,y = pad(f"LD{NLED}","2"); tx,ty = pad("TP7","1")
track(x,y,x,CH,"LD11_DOUT"); track(x,CH,tx,CH,"LD11_DOUT"); track(tx,CH,tx,ty,"LD11_DOUT")
routed += 3
for i in range(1, NLED+1):
    gx,gy = pad(f"C{9+i}","2"); via(gx,gy,"GND"); routed += 1

# ── SENSE. In rev C this is ~13 mm inside the bulge instead of ~70 mm down the strip:
# it never crosses the LED data channel and never runs beside the 5 V rail. It sits in
# the bulge GND pour, which is the guard.
sx,sy = pad("R7","2"); jx,jy = pad("J2","1"); gx,gy = pad("J2","2")
# J2 pin 1 (SENSE) sits left of pin 2 (GND), and the mounting tabs block the way down,
# so both nets exit UPWARD first. The lane order is what keeps them apart: the OUTER
# lane serves the NEARER web, the inner lane the farther one, so the two paths nest
# instead of crossing.
track(gx,gy, gx,20.6, "GND", 0.30); track(gx,20.6, 128.8,20.6, "GND", 0.30)
track(128.8,20.6, 128.8,32.0, "GND", 0.30); track(128.8,32.0, 133.0,32.0, "GND", 0.30)
# GND cannot reach its fingers on the top layer - the SENSE spine (x 136-137.2) is in
# the way for the full height of the comb. It drops to B.Cu, runs down the pad
# section's bare left margin, and comes up into the GND return bar under the comb.
via(133.0,32.0,"GND"); via(133.0,48.6,"GND")
track(133.0,32.0, 133.0,48.6, "GND", 0.30, pcbnew.B_Cu)
track(133.0,48.6, 140.0,48.6, "GND", 0.30); routed += 6
# SENSE exits LEFT and drops down its own lane at x=117.5, clear of J2's mounting tab
# at 119.15. GND goes up and over at y=20.6. That ordering is what stops them meeting.
track(jx,jy, 117.5,jy, "TOUCH_SENSE", 0.30); track(117.5,jy, 117.5,35.5, "TOUCH_SENSE", 0.30)
track(117.5,35.5, 137.0,35.5, "TOUCH_SENSE", 0.30); routed += 3   # onto the SENSE spine

# Back-side solder terminals, for wiring the pad from either face. Each is a pad on
# B.Cu with a via up to its bridge. Note this puts ONE via on SENSE, which §7.1 asks
# to avoid - it is a deliberate, inspectable feature rather than a routing artifact,
# and the boot-time baseline calibrates its ~0.5 pF away.
# SENSE's terminal hangs off the spine well below the bridge corridor, where the GND
# path cannot reach it; GND's sits on its own bridge.
via(134.5, 44.0, "TOUCH_SENSE"); via(131.5, 32.0, "GND"); routed += 2
track(136.4, 44.0, 134.5, 44.0, "TOUCH_SENSE", 0.30)
track(131.5, 32.0, 133.0, 32.0, "GND", 0.30); routed += 2
tsx,tsy = pad("TS1","1")
track(tsx,tsy, tsx,24.5, "TOUCH_SENSE", 0.30); track(tsx,24.5, 117.5,24.5, "TOUCH_SENSE", 0.30)
routed += 2

pcbnew.SaveBoard(B, board)
print("zones:", len([z for z in board.Zones()]), " tracks/vias added:", routed)
