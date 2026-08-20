# FL-11 rev B. Electronics moved off the strip into a rear bulge so the cable enters
# from the back at the middle. The LED row is continuous and unbroken.
#   strip  x 0..228, y 0..20      LEDs at y=11.000, 16.66667 pitch, x 10.000..176.667
#   bulge  x 74..118, y 20..46    MCU, power, USB-C (bottom side), touch front end
import os, sys, json
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

OUT, ESP, PADMAP = sys.argv[1], sys.argv[2], sys.argv[3]
KI = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/footprints")

VERSION  = "rev H"
DESIGNER = "Fionn Ferreira"
REPO     = "github.com/fionnf/linked-friend-lights-public"
COPYRIGHT= "\u00a9 2026 Fionn Ferreira"

W, H = 187.0, 20.0
# Bulge grew from 48x28 to 56x30 to fit three JST-PH plugs, so the touch pad needs
# no soldering in any configuration.
BX1, BX2, BY = 66.0, 130.0, 52.0          # electronics bulge, 64 x 32
PX1, PX2 = 130.0, 155.0                   # snap-off touch pad, beside the bulge
SLOT_X = 130.0                            # break line between them
# 15 LEDs at 11.13333 mm pitch. Fifteen at that spacing give a lit zone of exactly
# 167.00 mm - the lamp length stays put - while worst-case current drops to ~1.69 A,
# back under the 2 A PPTC hold and inside a 2.4 A supply. 20 LEDs needed neither.
NLED = 15
LED_X = [10.0 + 11.13333*i for i in range(NLED)]
LED_Y = 11.000

board = pcbnew.BOARD()
board.GetDesignSettings().SetBoardThickness(MM(1.6))
nets = {}
def N(name):
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); nets[name] = ni
    return nets[name]
for n in ["GND","VBUS_RAW","VBUS_F","+5V","LED_5V","+3V3","GATE","EN","CC1","CC2",
          "USB_DP_CONN","USB_DM_CONN","USB_DP","USB_DM","LED_DATA_3V3","LED_DATA_5V",
          "LED_DIN1","LD11_DOUT","TOUCH_GPIO","TOUCH_SENSE","BOOT_N","STRAP2","STRAP8",
          "UART_TX","UART_RX"]: N(n)
for i in range(1,NLED): N(f"D_{i}_{i+1}")

placed = {}
def put(ref, lib, fpname, x, y, rot=0, value="", bottom=False):
    path = ESP if lib == "Espressif" else f"{KI}/{lib}.pretty"
    fp = pcbnew.FootprintLoad(path, fpname)
    if fp is None: raise SystemExit(f"MISSING {lib}:{fpname}")
    fp.SetPosition(VECTOR2I(MM(x), MM(y)))
    fp.SetReference(ref); fp.SetValue(value or ref)
    board.Add(fp)                       # must be owned by the board before Flip
    if bottom: fp.Flip(VECTOR2I(MM(x), MM(y)), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    if rot: fp.SetOrientationDegrees(rot)
    placed[ref] = fp; return fp

R0402=("Resistor_SMD","R_0402_1005Metric"); C0402=("Capacitor_SMD","C_0402_1005Metric")
C0805=("Capacitor_SMD","C_0805_2012Metric")

# ── The strip: LEDs and their bypass caps. Nothing else lives here.
for i, x in enumerate(LED_X, start=1):
    put(f"LD{i}","LED_SMD","LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm", x, LED_Y, 90, "SK6812RGBW")
    # Cap sits fully inside the 5 V pour, long axis along x so it intrudes least on the
    # pour's 4.6 mm height. Pad 1 takes 5 V from the fill; pad 2 vias to the GND plane.
    put(f"C{9+i}", *C0402, x + 3.40, 15.10, 0, "100nF")

# ── The bulge. Antenna keep-out lands at x 93.4-106.6, y 38.9-44.3, pointing at the
# free y=46 edge - 21.9 mm clear of the nearest LED copper.
put("U1","Espressif","ESP32-C3-MINI-1", 98.0, 38.0, 180, "ESP32-C3-MINI-1-N4")
# U1 courtyard x 91.16-104.84, y 29.45-46.55; antenna keep-out y 40.9-46.3 facing the
# free y=52 edge, 22 mm clear of the nearest LED copper.
put("J1","Connector_USB","USB_C_Receptacle_HRO_TYPE-C-31-M-12", 82.0, 49.0, 0, "USB-C 16P")

# ── Left column
put("C1","Capacitor_SMD","CP_Elec_8x10", 78.0, 24.5, 0, "470uF/10V")
put("SW1","Button_Switch_SMD","SW_SPST_EVQP7C", 72.0, 40.0, 0, "BOOT")
put("U4","Package_TO_SOT_SMD","SOT-23-6", 86.5, 41.0, 0, "USBLC6-2SC6")
put("R1",*R0402, 84.0, 37.0, 0, "5k1"); put("R2",*R0402, 86.5, 37.0, 0, "5k1")
put("U2","Package_TO_SOT_SMD","SOT-23-5", 88.0, 31.5, 0, "SN74AHCT1G125")
put("C6",*C0402, 84.5, 31.5, 0, "100nF"); put("R11",*R0402, 88.5, 28.0, 0, "100R")
put("R3",*R0402, 88.0, 34.5, 0, "5k1"); put("C5",*C0805, 83.5, 34.5, 0, "22uF")

# ── Top band
put("F1","Resistor_SMD","R_1812_4532Metric", 93.0, 23.0, 0, "PPTC 2A/4A")
put("Q1","Package_TO_SOT_SMD","SOT-23", 100.0, 23.0, 0, "AO3401A")
put("R8",*R0402, 104.0, 22.4, 0, "100k"); put("C7",*C0402, 106.5, 22.4, 0, "100nF")
put("U3","Package_TO_SOT_SMD","SOT-23-5", 110.5, 23.0, 0, "AP2112K-3.3")
put("C2",*C0805, 114.5, 23.0, 0, "22uF"); put("C3",*C0805, 114.5, 26.5, 0, "22uF")
put("R9",*R0402, 93.0, 26.5, 0, "100k"); put("C8",*C0402, 95.5, 26.5, 0, "100nF")
put("R10",*R0402, 98.5, 26.5, 0, "4M7"); put("R7",*R0402, 101.0, 26.5, 0, "5k1")

# ── Between the module and the connector column
put("C4",*C0805, 110.0, 30.0, 0, "22uF"); put("C9",*C0402, 113.5, 30.0, 0, "100nF")
put("R4",*R0402, 108.0, 33.0, 0, "5k1"); put("R5",*R0402, 110.5, 33.0, 0, "5k1")
put("R6",*R0402, 113.0, 33.0, 0, "5k1")

put("H1","MountingHole","MountingHole_2.7mm_M2.5", 70.0, 46.0, 0, "M2.5")
put("H2","MountingHole","MountingHole_2.7mm_M2.5", 70.0, 33.5, 0, "M2.5")

TP = {"TP1":("LED_5V",134.0,18.5),"TP2":("+3V3",77.0,33.0),"TP3":("GND",77.0,36.0),
      "TP4":("GND",77.0,39.0),"TP5":("LED_DIN1",69.5,20.9),"TP6":("TOUCH_SENSE",103.5,26.5),
      "TP7":("LD11_DOUT",176.0,18.6),"TP8":("UART_TX",108.0,37.0),"TP9":("UART_RX",111.0,37.0),
      "TP10":("EN",100.0,18.5),"TP11":("VBUS_F",88.0,20.9)}
for ref,(net,x,y) in TP.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", x, y, 0, net)
    for p in fp.Pads(): p.SetNet(N(net))
# Three JST-PH plugs so nothing needs soldering:
#   J2  main board  - SENSE + GND, for a cable to the snapped-off pad
#   J3  pad section - the other end of that cable
#   J4  main board  - 3V3 / GND / SIG, for a commercial sensor module instead
JST2 = ("Connector_JST","JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal")
JST3 = ("Connector_JST","JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal")
# Rotated 90 deg so the cable leaves along the strip axis, in line with the LEDs,
# rather than out of the back of the bulge.
# Plugs live on the bulge only, rotated 90 so cables leave along the strip axis, in
# line with the LEDs. The pad section gets plain solder pads instead - it is snapped
# off rarely and soldered by hand when it is.
fp = put("J2", *JST2, 122.5, 26.5, 0, "SENSE+GND")
for pd in fp.Pads():
    pd.SetNet(N("TOUCH_SENSE") if pd.GetNumber()=="1" else N("GND"))
# Back-side solder terminals on the pad section, clear of the electrode area so the
# no-copper-under-the-pads rule still holds. Front side stays bare copper to solder to.
for idx,(xx,yy,net) in enumerate(((134.5,44.0,"TOUCH_SENSE"),(131.5,32.0,"GND")), start=1):
    fp = put(f"J3_{idx}","TestPoint","TestPoint_Pad_D1.0mm", xx, yy, 0, net, bottom=True)
    for pd in fp.Pads(): pd.SetNet(N(net))

# Solder terminals beside each plug, so the board still works with no connectors at
# all - JST housings are the one part likely to be missing from a hobby bench.
for ref,(xx,yy,net) in {"TS1":(118.0,20.8,"TOUCH_SENSE"), "TS2":(115.5,20.8,"GND"),
                        "TS3":(99.0,49.2,"+5V"),        "TS4":(101.5,49.2,"GND"),
                        "TS5":(104.0,49.2,"TOUCH_SENSE")}.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", xx, yy, 0, net)
    for pd in fp.Pads(): pd.SetNet(N(net))
# J4 matches a commercial module's 5V / GND / SIG pinout. SIG lands on TOUCH_SENSE,
# NOT on the GPIO: a 5V-powered TTP223 drives its output to 5 V and the ESP32-C3 is
# not 5V tolerant (3.6 V absolute max). Going in through R7's 5.1 k means the C3's
# clamp diode sees ~0.33 mA instead of a direct 5 V drive - the series resistor that
# was already there for ESD does this job for free.
# J4 moved out of the break corridor so SENSE and GND can both reach the pad
# section without crossing each other or J2's mounting tabs.
fp = put("J4", *JST3, 111.0, 45.0, 0, "5V/GND/SIG")
for pd in fp.Pads():
    n = {"1":"+5V","2":"GND","3":"TOUCH_SENSE"}.get(pd.GetNumber(),"GND")
    pd.SetNet(N(n))

CONN = {
 ("F1","1"):"VBUS_RAW", ("F1","2"):"VBUS_F",
 ("U4","1"):"USB_DM_CONN", ("U4","2"):"GND", ("U4","3"):"USB_DP_CONN",
 ("U4","4"):"USB_DP", ("U4","5"):"VBUS_RAW", ("U4","6"):"USB_DM",
 ("R1","1"):"CC1", ("R1","2"):"GND", ("R2","1"):"CC2", ("R2","2"):"GND",
 ("Q1","1"):"GATE", ("Q1","2"):"VBUS_F", ("Q1","3"):"+5V",
 ("R8","1"):"GATE", ("R8","2"):"GND", ("C7","1"):"GATE", ("C7","2"):"VBUS_F",
 ("C1","1"):"LED_5V", ("C1","2"):"GND",
 ("U3","1"):"+5V", ("U3","2"):"GND", ("U3","3"):"+5V", ("U3","5"):"+3V3",
 ("C2","1"):"+5V", ("C2","2"):"GND", ("C3","1"):"+3V3", ("C3","2"):"GND",
 ("R9","1"):"+3V3", ("R9","2"):"EN", ("C8","1"):"EN", ("C8","2"):"GND",
 ("C4","1"):"+3V3", ("C4","2"):"GND", ("C9","1"):"+3V3", ("C9","2"):"GND",
 ("U2","1"):"GND", ("U2","2"):"LED_DATA_3V3", ("U2","3"):"GND",
 ("U2","4"):"LED_DATA_5V", ("U2","5"):"LED_5V",
 ("C6","1"):"LED_5V", ("C6","2"):"GND", ("C5","1"):"LED_5V", ("C5","2"):"GND",
 ("R3","1"):"LED_DATA_3V3", ("R3","2"):"GND",
 ("R11","1"):"LED_DATA_5V", ("R11","2"):"LED_DIN1",
 ("R10","1"):"TOUCH_GPIO", ("R10","2"):"GND",
 ("R7","1"):"TOUCH_GPIO", ("R7","2"):"TOUCH_SENSE",
 ("R4","1"):"+3V3", ("R4","2"):"STRAP2", ("R5","1"):"+3V3", ("R5","2"):"STRAP8",
 ("R6","1"):"+3V3", ("R6","2"):"BOOT_N",
 ("SW1","1"):"BOOT_N", ("SW1","2"):"GND",
}
PAD = json.load(open(PADMAP))
for sig, net in (("IO5","LED_DATA_3V3"),("IO3","TOUCH_GPIO"),("IO2","STRAP2"),
                 ("IO8","STRAP8"),("IO9","BOOT_N"),("IO18","USB_DM"),("IO19","USB_DP"),
                 ("IO20","UART_RX"),("IO21","UART_TX"),("EN","EN"),("3V3","+3V3")):
    CONN[("U1", PAD[sig])] = net
for g in PAD["GND"]: CONN[("U1", g)] = "GND"
for i in range(1,NLED+1):
    CONN[(f"LD{i}","1")]="LED_5V"; CONN[(f"LD{i}","3")]="GND"
    CONN[(f"LD{i}","2")]=f"D_{i}_{i+1}" if i<NLED else "LD11_DOUT"
    CONN[(f"LD{i}","4")]="LED_DIN1" if i==1 else f"D_{i-1}_{i}"
    CONN[(f"C{9+i}","1")]="LED_5V"; CONN[(f"C{9+i}","2")]="GND"
for pd, net in (("A1","GND"),("B1","GND"),("A12","GND"),("B12","GND"),
                ("A4","VBUS_RAW"),("B4","VBUS_RAW"),("A9","VBUS_RAW"),("B9","VBUS_RAW"),
                ("A5","CC1"),("B5","CC2"),("A6","USB_DP_CONN"),("B6","USB_DP_CONN"),
                ("A7","USB_DM_CONN"),("B7","USB_DM_CONN"),("SH","GND")):
    CONN[("J1",pd)] = net

unmatched=[]
for (ref,pn), net in CONN.items():
    fp = placed.get(ref)
    if fp is None: unmatched.append((ref,pn,"NO FP")); continue
    hit = False
    for p in fp.Pads():
        if p.GetNumber()==pn: p.SetNet(N(net)); hit = True    # ALL matching pads
    if not hit: unmatched.append((ref,pn,net))

def seg(x1,y1,x2,y2):
    s=pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I(MM(x1),MM(y1))); s.SetEnd(VECTOR2I(MM(x2),MM(y2)))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)

# Outline: strip with the bulge hanging off the y=20 edge. LED row never interrupted.
PY1 = 22.0                                  # pad section starts here; y 20-22 is a notch
# Boundary, traced once: strip, then down the bulge's right edge, around the notch,
# round the pad, along the bottom, up the bulge's left edge, back along the strip.
for a in [(0,0,W,0),(W,0,W,H),(W,H,PX1,H),(PX1,H,PX1,PY1),(PX1,PY1,PX2,PY1),
          (PX2,PY1,PX2,BY),(PX2,BY,BX1,BY),(BX1,BY,BX1,H),(BX1,H,0,H),(0,H,0,0)]:
    seg(*a)

# Break line: one edge only, x=120 between bulge and pad. Retained by two 0.9 mm webs
# carrying SENSE and GND plus two 0.4 mm corner ligaments - about 2.6 mm against rev C's
# 4.3 mm, and the notch above leaves the pad cantilevered so it can be gripped and bent.
WEB = 1.3
edges=[PY1+0.4]
for cy in (32.0, 35.5): edges += [cy-WEB/2, cy+WEB/2]
edges.append(BY-0.4)
for i in range(0,len(edges),2):
    y1,y2 = edges[i], edges[i+1]
    if y2-y1 > 0.05:
        seg(SLOT_X-0.4,y1,SLOT_X-0.4,y2); seg(SLOT_X+0.4,y1,SLOT_X+0.4,y2)
        seg(SLOT_X-0.4,y1,SLOT_X+0.4,y1); seg(SLOT_X-0.4,y2,SLOT_X+0.4,y2)

# ── Silkscreen. JLC's floor is 0.8 mm height / 0.15 mm stroke; below that it prints
# mushy or gets dropped. Nothing here goes under that.
def silk(txt, x, y, size=0.9, thick=0.15, layer=pcbnew.F_SilkS):
    size = max(size, 0.8); thick = max(thick, 0.15)
    t = pcbnew.PCB_TEXT(board); t.SetText(txt)
    t.SetPosition(VECTOR2I(MM(x), MM(y))); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(thick))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    board.Add(t); return t

# Reference designators: keep them where a human needs them at bring-up, hide them in the
# dense runs where they only collide. The CPL carries placement, not the silkscreen.
for ref, fp in placed.items():
    r = fp.Reference()
    r.SetTextSize(VECTOR2I(MM(0.8), MM(0.8))); r.SetTextThickness(MM(0.15))
    if ref.startswith(("TP","J2_","J3_","J4_","H")) or (ref.startswith("C") and ref[1:].isdigit() and int(ref[1:]) >= 10):
        r.SetVisible(False)
    fp.Value().SetVisible(ref.startswith("J4_"))   # J4 pads label themselves

# Identity, in the clear band beside the LED row: below the 5 V pour (ends y=17.0), above
# the board edge, right of x=120 where the DIN trace never runs. Bare soldermask under it.
silk("LINKED FRIEND LIGHTS", 150.0, 17.9, 1.0, 0.17)
silk(f"FL-11 {VERSION}   \u00b7   {COPYRIGHT}", 150.0, 19.0, 0.8, 0.15)
silk(REPO, 40.0, 19.0, 0.8, 0.15)
silk("LINKED FRIEND LIGHTS", 96.0, 51.0, 0.8, 0.15)
silk(f"FL-11 {VERSION} TOUCH", 142.5, 31.0, 0.8, 0.15)
silk(COPYRIGHT, 142.5, 51.0, 0.8, 0.15)
silk("CUT TRACES", 122.5, 20.8, 0.8, 0.15)

pcbnew.SaveBoard(OUT, board)
print("PLACED:", len(placed), " NETS:", len(nets),
      " UNMATCHED:", unmatched if unmatched else "none")
