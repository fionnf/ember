# FL-11 rev B pours and routing.
import sys, pcbnew
from pcbnew import VECTOR2I, FromMM as MM
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
rect(pcbnew.F_Cu, "GND",    0.4, 0.40, 195.0, 9.30, prio=1)
rect(pcbnew.F_Cu, "LED_5V", 0.4, 12.40, 195.0, 17.00, prio=1)
# SENSE lane guards. In rev B the sense line cannot use the y=1.4 channel: it would
# have to cross the LED data channel, and every x between LEDs carries a hop. It runs
# in the y=18.6 lane instead, guarded above and below, and crosses the pours only once.
rect(pcbnew.F_Cu, "GND", 118.0, 17.40, 190.0, 17.90, prio=2)
rect(pcbnew.F_Cu, "GND", 118.0, 19.20, 190.0, 19.70, prio=2)
# Bottom plane covers strip + bulge as one L, stopping short of the break slot
zone(pcbnew.B_Cu, "GND", [(0.4,0.4),(195.0,0.4),(195.0,19.6),(119.6,19.6),
                          (119.6,47.6),(72.4,47.6),(72.4,19.6),(0.4,19.6)], prio=0, solid=True)
# Bulge: 5 V feed and GND, both necked around the antenna keep-out (DRC enforces it)
rect(pcbnew.F_Cu, "LED_5V", 72.4, 20.0, 119.6, 28.6, prio=1)
rect(pcbnew.F_Cu, "GND",    72.4, 29.0, 119.6, 47.6, prio=1)
# Tab electrodes
rect(pcbnew.F_Cu, "TOUCH_SENSE", 200.0, 1.20, 225.0, 9.20,  prio=1, solid=True)
rect(pcbnew.F_Cu, "GND",         200.0, 10.60, 225.0, 18.60, prio=1)

def pad(ref, num):
    fp = board.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber()==num:
            v=p.GetPosition(); return v.x/1e6, v.y/1e6
    raise SystemExit(f"no pad {ref}.{num}")

routed = 0
CH = 11.0
for i in range(1, 11):
    x1,y1 = pad(f"LD{i}","2"); x2,y2 = pad(f"LD{i+1}","4"); net=f"D_{i}_{i+1}"
    track(x1,y1,x1,CH,net); track(x1,CH,x2,CH,net); track(x2,CH,x2,y2,net); routed += 3
# Buffer output leaves the bulge and runs ~80 mm to LD1. Past the ~75 mm critical
# length, so R11 is now a 100R series termination (AHCT Zout 15-25R + ~120R trace).
x,y = pad("U2","4"); rx,ry = pad("R11","1"); track(x,y,rx,ry,"LED_DATA_5V"); routed += 1
# DIN must NOT share the y=11 data channel - it would cross every hop. It runs
# below the 5 V pour at y=18.6, then climbs at x=4.0, clear of LD1's body.
x,y = pad("R11","2"); dx,dy = pad("LD1","4")
DIN_Y, DIN_X, EXIT = 18.6, 4.0, 73.5
track(x,y, x,37.5, "LED_DIN1"); track(x,37.5, EXIT,37.5, "LED_DIN1")
track(EXIT,37.5, EXIT,DIN_Y, "LED_DIN1"); track(EXIT,DIN_Y, DIN_X,DIN_Y, "LED_DIN1")
track(DIN_X,DIN_Y, DIN_X,dy, "LED_DIN1"); track(DIN_X,dy, dx,dy, "LED_DIN1"); routed += 6
x,y = pad("LD11","2"); tx,ty = pad("TP7","1")
track(x,y,x,CH,"LD11_DOUT"); track(x,CH,tx,CH,"LD11_DOUT"); track(tx,CH,tx,ty,"LD11_DOUT")
routed += 3
for i in range(1,12):
    gx,gy = pad(f"C{9+i}","2"); via(gx,gy,"GND"); routed += 1

# ── SENSE: out of the bulge at x=121? No - the bulge ends at 118, so it climbs at
# x=120.5 in the strip, threading the gap between LD8 (126.667) and LD7 (110.0).
# It crosses both pours once, at right angles, which is the minimum coupling geometry.
# SENSE: bulge -> y=18.6 guarded lane -> climbs at x=188, which is past LD11_DOUT's
# end at 186, so it is the only place it can cross the data channel without a hop there.
SY = 18.6
sx,sy = pad("R7","2")
track(sx,sy, sx,29.0, "TOUCH_SENSE", 0.30); track(sx,29.0, 118.5,29.0, "TOUCH_SENSE", 0.30)
track(118.5,29.0, 118.5,SY, "TOUCH_SENSE", 0.30)
tx,ty = pad("TP6","1"); track(tx,ty, sx,ty, "TOUCH_SENSE", 0.30); routed += 4
jx,jy = pad("J2_1","1")
track(118.5,SY, 188.0,SY, "TOUCH_SENSE", 0.30); track(188.0,SY, 188.0,jy, "TOUCH_SENSE", 0.30)
track(188.0,jy, jx,jy, "TOUCH_SENSE", 0.30); routed += 3
track(jx,jy, 202.0,jy, "TOUCH_SENSE", 0.30); routed += 1
gx,gy = pad("J2_2","1"); track(gx,gy, 202.0,gy, "GND", 0.5); routed += 1

pcbnew.SaveBoard(B, board)
print("zones:", len([z for z in board.Zones()]), " tracks/vias added:", routed)
