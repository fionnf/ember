import sys, pcbnew
from pcbnew import VECTOR2I, FromMM as MM
B = sys.argv[1]
board = pcbnew.LoadBoard(B)
nets = board.GetNetsByName()
def N(n): return nets[n]

KEEP = []   # SetOutline does not take ownership; a GC'd SHAPE_POLY_SET segfaults on save
def zone(layer, net, x1,y1,x2,y2, prio=0, solid=False):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer); z.SetNet(N(net)); z.SetAssignedPriority(prio)
    z.SetIsFilled(False)
    poly = pcbnew.SHAPE_POLY_SET(); poly.NewOutline()
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):
        poly.Append(MM(x), MM(y))
    z.SetOutline(poly); KEEP.append(poly)
    z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.25)); z.SetThermalReliefSpokeWidth(MM(0.4))
    board.Add(z); return z

def track(x1,y1,x2,y2,net,w=0.25,layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(VECTOR2I(MM(x1),MM(y1))); t.SetEnd(VECTOR2I(MM(x2),MM(y2)))
    t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(N(net))
    board.Add(t); return t

def via(x,y,net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(MM(x),MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3))
    v.SetNet(N(net)); board.Add(v); return v

# ── Cross-section, mirrored from the §7.1 table. The LED package puts VDD and DIN on
# the same side, so a head-to-tab data flow forces VDD to the y=20 side. Mirroring keeps
# the clean daisy chain AND increases SENSE-to-5V separation from 9.1 mm to ~12 mm.
# This also makes the doc self-consistent: §7.2 puts the bypass caps at y=15.50, which
# only works if the 5 V pour is the bottom band.
zone(pcbnew.F_Cu, "GND",    56.0, 2.70, 249.0, 9.30,  prio=1)
zone(pcbnew.F_Cu, "LED_5V", 54.0, 12.40, 249.0, 17.00, prio=1)
zone(pcbnew.B_Cu, "GND",     0.40, 0.40, 249.0, 19.60, prio=0)
# Guard rails either side of the SENSE channel, now at the y=0 edge
zone(pcbnew.F_Cu, "GND", 56.0, 0.40, 249.0, 0.90, prio=2)
zone(pcbnew.F_Cu, "GND", 56.0, 1.90, 249.0, 2.40, prio=2)
# Tab electrodes: SENSE at the y=0 side to meet the channel, GND return alongside
zone(pcbnew.F_Cu, "TOUCH_SENSE", 254.0, 1.20, 279.0, 9.20,  prio=1, solid=True)
zone(pcbnew.F_Cu, "GND",         254.0, 10.60, 279.0, 18.60, prio=1)

def pad(ref, num):
    fp = board.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            v = p.GetPosition(); return v.x/1e6, v.y/1e6
    raise SystemExit(f"no pad {ref}.{num}")

routed = 0
# ── Step 11: DOUT -> DIN. At 90 deg, DIN is top-left and DOUT bottom-right, so every
# hop stays inside the inter-package gap and no two hops cross.
CH = 11.0
for i in range(1, 11):
    x1,y1 = pad(f"LD{i}", "2"); x2,y2 = pad(f"LD{i+1}", "4")
    net = f"D_{i}_{i+1}"
    track(x1,y1, x1,CH, net); track(x1,CH, x2,CH, net); track(x2,CH, x2,y2, net)
    routed += 3
x,y = pad("U2","4"); rx,ry = pad("R11","1"); track(x,y, rx,ry, "LED_DATA_5V"); routed += 1
x,y = pad("R11","2"); dx,dy = pad("LD1","4")
track(x,y, x,CH, "LED_DIN1"); track(x,CH, dx,CH, "LED_DIN1"); track(dx,CH, dx,dy, "LED_DIN1")
routed += 3
x,y = pad("LD11","2"); tx,ty = pad("TP7","1")
track(x,y, x,CH, "LD11_DOUT"); track(x,CH, tx,CH, "LD11_DOUT"); track(tx,CH, tx,ty, "LD11_DOUT")
routed += 3
for i in range(1, 12):
    gx,gy = pad(f"C{9+i}", "2"); via(gx, gy, "GND"); routed += 1

# ── Step 10: SENSE. Top layer, zero vias, straight down the guarded channel at y=1.40.
SY = 1.40
sx,sy = pad("R7","2"); track(sx,sy, sx,SY, "TOUCH_SENSE", 0.30); routed += 1
track(sx,SY, 243.0,SY, "TOUCH_SENSE", 0.30)
tx,ty = pad("TP6","1"); track(tx,ty, tx,SY, "TOUCH_SENSE", 0.30); routed += 2
jx,jy = pad("J2_1","1")
track(243.0,SY, 243.0,jy, "TOUCH_SENSE", 0.30); track(243.0,jy, jx,jy, "TOUCH_SENSE", 0.30)
routed += 2
# across the centre bridge into the tab electrode
track(jx,jy, 256.0,jy, "TOUCH_SENSE", 0.30); routed += 1
# GND return across the bridge to the tab's return electrode
gx,gy = pad("J2_2","1"); track(gx,gy, 256.0,gy, "GND", 0.5); routed += 1
pcbnew.SaveBoard(B, board)
print("zones:", len([z for z in board.Zones()]), " tracks/vias added:", routed)
