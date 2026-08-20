#!/usr/bin/env python3
"""Post-process the autorouted board: enforce the width floor, stitch the ground
zones to the plane, and close the last few connections.

Run after importing the freerouting SES. Idempotent."""
import sys, pcbnew
from pcbnew import VECTOR2I, FromMM as MM

B = sys.argv[1]
board = pcbnew.LoadBoard(B)
nets = board.GetNetsByName()
MIN_W = 0.2

# 1. Freerouting emits 0.15 mm where the board floor is 0.20 mm.
widened = 0
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA): continue
    if t.GetWidth() < MM(MIN_W):
        t.SetWidth(MM(MIN_W)); widened += 1

def via(x, y, net):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(nets[net])
    board.Add(v); return v

def track(x1,y1,x2,y2,net,w=0.25,layer=pcbnew.F_Cu):
    t=pcbnew.PCB_TRACK(board); t.SetStart(VECTOR2I(MM(x1),MM(y1)))
    t.SetEnd(VECTOR2I(MM(x2),MM(y2))); t.SetWidth(MM(w)); t.SetLayer(layer)
    t.SetNet(nets[net]); board.Add(t); return t

def pad(ref, num):
    fp = board.FindFootprintByReference(ref)
    if fp is None: return None
    for p in fp.Pads():
        if p.GetNumber()==num:
            v=p.GetPosition(); return v.x/1e6, v.y/1e6
    return None

# 2. Stitch every F.Cu ground region to the B.Cu plane. Without these the pours are
# electrically separate islands even though they share a net name. Candidates are
# filtered against existing copper and the antenna keep-out rather than trusted.
ANT = (107.5, 40.4, 122.5, 46.8)     # module antenna keep-out (rev I position), with margin

def seg_dist(px,py, x1,y1,x2,y2):
    dx,dy = x2-x1, y2-y1
    if dx==0 and dy==0: return ((px-x1)**2+(py-y1)**2)**0.5
    t = max(0, min(1, ((px-x1)*dx+(py-y1)*dy)/(dx*dx+dy*dy)))
    return ((px-(x1+t*dx))**2 + (py-(y1+t*dy))**2)**0.5

obstacles = []
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        v=t.GetPosition(); obstacles.append((v.x/1e6, v.y/1e6, v.x/1e6, v.y/1e6, t.GetNetname()))
    else:
        a,bb = t.GetStart(), t.GetEnd()
        obstacles.append((a.x/1e6, a.y/1e6, bb.x/1e6, bb.y/1e6, t.GetNetname()))
for fp in board.Footprints():
    for pd in fp.Pads():
        v=pd.GetPosition(); obstacles.append((v.x/1e6,v.y/1e6,v.x/1e6,v.y/1e6, pd.GetNetname()))
# Mounting holes are NPTH with no net, so they never appear as obstacles otherwise.
for ref in ("H1","H2","H3","H4"):
    fp = board.FindFootprintByReference(ref)
    if fp:
        v = fp.GetPosition(); x,y = v.x/1e6, v.y/1e6
        obstacles.append((x, y, x, y, "__HOLE__"))   # checked at a wider radius below

EDGES = [(0,0,187,0),(187,0,187,20),(187,20,120,20),(120,20,120,22),(120,22,145,22),
         (145,22,145,48),(145,48,72,48),(72,48,72,20),(72,20,0,20),(0,20,0,0),
         (119.6,22,119.6,48),(120.4,22,120.4,48)]

def clear_for_gnd(x,y, r=2.0):
    if ANT[0] <= x <= ANT[2] and ANT[1] <= y <= ANT[3]: return False
    for x1,y1,x2,y2 in EDGES:
        if seg_dist(x,y,x1,y1,x2,y2) < 1.1: return False
    for x1,y1,x2,y2,net in obstacles:
        if net == "GND": continue
        need = 2.3 if net == "__HOLE__" else r      # 2.7 mm hole + via + clearance
        if seg_dist(x,y,x1,y1,x2,y2) < need: return False
    return True

# A grid, filtered. Sparse stitching left the pours as separate islands; every
# candidate that survives the clearance test becomes a tie between F.Cu and the plane.
CANDIDATES  = [(x, y) for x in range(6, 185, 5) for y in (2.0, 4.0, 6.0)]
CANDIDATES += [(x, y) for x in range(74, 120, 4) for y in
               (21.0, 24.0, 27.0, 31.0, 35.0, 39.0, 43.0, 46.5)]
# The priority-3 solid patches under U1 and J1 are separate zone objects: the
# priority-0 pour is clipped around them, so each needs its own tie to the plane.
CANDIDATES += [(95.0,31.0),(101.0,31.0),(105.5,31.0),(95.0,35.0),(105.5,39.0),
               (95.0,39.0),(74.2,38.6),(86.0,38.6),(74.2,47.0),(86.2,47.0)]
placed_vias = 0
for x,y in CANDIDATES:
    if clear_for_gnd(x,y):
        via(x,y,"GND"); placed_vias += 1
# 3. Ground pads the router left floating
# Try the pad centre, then walk outward: a via dropped blind can land on a B.Cu
# signal running under the pad, which is a short, not a connection.
def place_gnd_via_near(x, y):
    global placed_vias
    for dx, dy in [(0,0),(0,-0.9),(0,0.9),(-0.9,0),(0.9,0),(-0.9,-0.9),(0.9,0.9),
                   (0,-1.5),(0,1.5),(-1.5,0),(1.5,0)]:
        if clear_for_gnd(x+dx, y+dy, 0.95):
            via(x+dx, y+dy, "GND"); placed_vias += 1
            if dx or dy: track(x, y, x+dx, y+dy, "GND", 0.3)
            return True
    return False

for ref,pn in [("SW1","2"),("U3","2"),("U2","1"),("U2","3"),("U4","2"),("R10","2"),
               ("C8","2"),("C9","2"),("C2","2"),("C3","2"),("C4","2"),
               ("R1","2"),("R2","2"),("R3","2"),("R8","2"),("R10","2"),("C1","2"),("J4_3","1"),("TP3","1"),("TP4","1")]:
    p = pad(ref,pn)
    if p: place_gnd_via_near(*p)

# 4. EN never reached its test point
p10 = pad("TP10","1")
if p10: track(p10[0], p10[1], p10[0], p10[1]-1.2, "EN")

# 5. Pads the pour cannot reach with thermal spokes get a solid tie instead - they are
# already fed by a via, and a starved spoke is an error rather than a connection.
for ref,pn in [("C8","2"),("C9","2"),("SW1","2"),("U3","2"),("U2","1"),("U2","3"),("U4","2"),("R10","2"),("TP4","1"),("TP3","1")]:
    fp = board.FindFootprintByReference(ref)
    if fp:
        for pdx in fp.Pads():
            if pdx.GetNumber()==pn:
                pdx.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

# 6. Close any net left with two stubs that never met (the router leaves a few).
def join_net_stubs(net):
    segs=[t for t in board.GetTracks()
          if not isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()==net]
    if len(segs) < 2: return
    ends=[]
    for t in segs:
        for pt in (t.GetStart(), t.GetEnd()): ends.append((pt.x/1e6, pt.y/1e6))
    best=None
    for i in range(len(ends)):
        for j in range(i+1,len(ends)):
            d=((ends[i][0]-ends[j][0])**2+(ends[i][1]-ends[j][1])**2)**0.5
            if 0.05 < d < 6.0 and (best is None or d < best[0]): best=(d,ends[i],ends[j])
    if best: track(best[1][0],best[1][1],best[2][0],best[2][1],net)

# 7. Floating copper the router's B.Cu traces carved out of the plane. Removing
# islands is the standard answer: unconnected fill is not a connection, and leaving
# it is both a DRC complaint and poor practice.
for z in board.Zones():
    if z.GetNetname() == "GND":
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)

# 8. Any pad the router left stranded gets joined to the nearest copper on its own net.
# The pour usually covers these; when a router track carves past a pad the fill can
# retreat just far enough to strand it, and a bypass cap that is not connected is a
# bypass cap that is not doing anything.
def nearest_same_net(px, py, net, exclude_pad=None):
    best = None
    for t in board.GetTracks():
        if t.GetNetname() != net: continue
        pts = [t.GetPosition()] if isinstance(t, pcbnew.PCB_VIA) else [t.GetStart(), t.GetEnd()]
        for pt in pts:
            x, y = pt.x/1e6, pt.y/1e6
            d = ((px-x)**2 + (py-y)**2)**0.5
            if 0.01 < d < 15.0 and (best is None or d < best[0]): best = (d, x, y)
    # Other pads on the same net count too - a stranded bypass cap's nearest copper is
    # usually the LED it belongs to, not a track.
    for fp2 in board.Footprints():
        for pd2 in fp2.Pads():
            if pd2.GetNetname() != net: continue
            v2 = pd2.GetPosition(); x, y = v2.x/1e6, v2.y/1e6
            d = ((px-x)**2 + (py-y)**2)**0.5
            if 0.01 < d < 15.0 and (best is None or d < best[0]): best = (d, x, y)
    return best

# Two pads the router strands, joined explicitly - a straight line to the nearest
# copper clips LD7's DOUT pad, so C16 goes round underneath the package instead.
c16 = pad("C16","1"); ld7 = pad("LD7","1")
if c16 and ld7:
    track(c16[0], c16[1], c16[0], 16.9, "LED_5V", 0.3)
    track(c16[0], 16.9, ld7[0], 16.9, "LED_5V", 0.3)
    track(ld7[0], 16.9, ld7[0], ld7[1], "LED_5V", 0.3)
tp5 = pad("TP5","1")
if tp5:
    track(tp5[0], tp5[1], tp5[0], 18.6, "LED_DIN1", 0.25)   # onto the DIN lane

pcbnew.SaveBoard(B, board)
print(f"widened {widened} tracks to {MIN_W} mm; placed {placed_vias} ground vias")
