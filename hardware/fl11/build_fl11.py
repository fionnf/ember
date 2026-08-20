# FL-11 rev B. Electronics moved off the strip into a rear bulge so the cable enters
# from the back at the middle. The LED row is continuous and unbroken.
#   strip  x 0..228, y 0..20      LEDs at y=11.000, 16.66667 pitch, x 10.000..176.667
#   bulge  x 74..118, y 20..46    MCU, power, USB-C (bottom side), touch front end
import os, sys, json
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

OUT, ESP, PADMAP = sys.argv[1], sys.argv[2], sys.argv[3]
KI = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/footprints")

VERSION  = "rev E"
DESIGNER = "Fionn Ferreira"
REPO     = "github.com/fionnf/linked-friend-lights-public"

W, H = 187.0, 20.0
BX1, BX2, BY = 72.0, 120.0, 48.0          # electronics bulge
PX1, PX2 = 120.0, 145.0                   # snap-off touch pad, beside the bulge
SLOT_X = 120.0                            # break line between them
LED_X = [10.0 + 16.66667*i for i in range(11)]
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
for i in range(1,11): N(f"D_{i}_{i+1}")

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
    put(f"C{9+i}", *C0402, x + 3.40, 15.50, 90, "100nF")

# ── The bulge. Antenna keep-out lands at x 93.4-106.6, y 38.9-44.3, pointing at the
# free y=46 edge - 21.9 mm clear of the nearest LED copper.
put("U1","Espressif","ESP32-C3-MINI-1", 100.0, 38.0, 180, "ESP32-C3-MINI-1-N4")
# U1 courtyard x 93.16-106.84, y 29.45-46.55; antenna keep-out lands at y 40.9-46.3,
# facing the free y=48 edge. Everything below is placed clear of that box.
put("J1","Connector_USB","USB_C_Receptacle_HRO_TYPE-C-31-M-12", 80.0, 43.8, 0,
    "USB-C 16P")   # TOP side. Horizontal receptacle: the plug still enters along the
                   # board plane from the rear y=48 edge, so rear entry is unchanged and
                   # the board goes back to single-sided assembly.
put("U4","Package_TO_SOT_SMD","SOT-23-6", 89.2, 41.5, 0, "USBLC6-2SC6")
put("R1",*R0402, 87.5, 45.5, 0, "5k1"); put("R2",*R0402, 90.5, 45.5, 0, "5k1")
put("C1","Capacitor_SMD","CP_Elec_8x10", 80.0, 25.0, 0, "470uF/10V")
put("SW1","Button_Switch_SMD","SW_SPST_EVQP7C", 90.0, 24.0, 0, "BOOT")
put("F1","Resistor_SMD","R_1812_4532Metric", 98.0, 23.0, 0, "PPTC 2A/4A")
put("Q1","Package_TO_SOT_SMD","SOT-23", 105.0, 23.0, 0, "AO3401A")
put("R8",*R0402, 110.0, 22.0, 0, "100k"); put("C7",*C0402, 112.5, 22.0, 0, "100nF")
put("U3","Package_TO_SOT_SMD","SOT-23-5", 116.0, 25.0, 0, "AP2112K-3.3")
put("C3",*C0805, 110.0, 25.5, 0, "22uF"); put("C2",*C0805, 110.0, 30.5, 0, "22uF")
put("R9",*R0402, 95.0, 27.0, 0, "100k"); put("C8",*C0402, 97.5, 27.0, 0, "100nF")
put("U2","Package_TO_SOT_SMD","SOT-23-5", 88.5, 31.5, 0, "SN74AHCT1G125")
put("C6",*C0402, 84.5, 31.5, 0, "100nF"); put("R11",*R0402, 88.5, 35.0, 0, "100R")
put("R3",*R0402, 91.5, 31.5, 0, "5k1"); put("C5",*C0805, 84.0, 34.5, 0, "22uF")
put("C4",*C0805, 114.5, 30.5, 0, "22uF"); put("C9",*C0402, 110.0, 33.0, 0, "100nF")
put("R10",*R0402, 102.0, 27.0, 0, "4M7"); put("R7",*R0402, 104.5, 27.0, 0, "5k1")
put("R4",*R0402, 114.5, 33.5, 0, "5k1"); put("R5",*R0402, 110.0, 36.0, 0, "5k1")
put("R6",*R0402, 114.5, 36.0, 0, "5k1")
put("H1","MountingHole","MountingHole_2.7mm_M2.5", 76.5, 34.0, 0, "M2.5")
put("H2","MountingHole","MountingHole_2.7mm_M2.5", 114.0, 43.0, 0, "M2.5")

TP = {"TP1":("LED_5V",116.0,21.0),"TP2":("+3V3",118.0,30.5),"TP3":("GND",118.0,33.0),
      "TP4":("GND",122.5,44.5),"TP5":("LED_DIN1",80.0,37.0),"TP6":("TOUCH_SENSE",106.5,27.0),
      "TP7":("LD11_DOUT",183.0,15.5),"TP8":("UART_TX",108.5,39.5),"TP9":("UART_RX",108.5,42.0),
      "TP10":("EN",108.5,44.5),"TP11":("VBUS_F",93.5,21.5)}
for ref,(net,x,y) in TP.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", x, y, 0, net)
    for p in fp.Pads(): p.SetNet(N(net))
for ref, x in (("J2",117.5),("J3",128.0)):
    for idx,(yy,net) in enumerate(((28.0,"TOUCH_SENSE"),(41.0,"GND")), start=1):
        fp = put(f"{ref}_{idx}","TestPoint","TestPoint_Pad_D1.0mm", x, yy, 0, net)
        for p in fp.Pads(): p.SetNet(N(net))

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
for i in range(1,12):
    CONN[(f"LD{i}","1")]="LED_5V"; CONN[(f"LD{i}","3")]="GND"
    CONN[(f"LD{i}","2")]=f"D_{i}_{i+1}" if i<11 else "LD11_DOUT"
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
for cy in (28.0, 41.0): edges += [cy-WEB/2, cy+WEB/2]
edges.append(BY-0.4)
for i in range(0,len(edges),2):
    y1,y2 = edges[i], edges[i+1]
    if y2-y1 > 0.05:
        seg(SLOT_X-0.4,y1,SLOT_X-0.4,y2); seg(SLOT_X+0.4,y1,SLOT_X+0.4,y2)
        seg(SLOT_X-0.4,y1,SLOT_X+0.4,y1); seg(SLOT_X-0.4,y2,SLOT_X+0.4,y2)

pcbnew.SaveBoard(OUT, board)
print("PLACED:", len(placed), " NETS:", len(nets),
      " UNMATCHED:", unmatched if unmatched else "none")
