# EM-15 rev B. Electronics moved off the strip into a rear bulge so the cable enters
# from the back at the middle. The LED row is continuous and unbroken.
#   strip  x 0..228, y 0..20      LEDs at y=11.000, 16.66667 pitch, x 10.000..176.667
#   bulge  x 74..118, y 20..46    MCU, power, USB-C (bottom side), touch front end
import os, sys, json
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

OUT, ESP, PADMAP = sys.argv[1], sys.argv[2], sys.argv[3]
KI = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/footprints")

VERSION  = "rev I"
DESIGNER = "Fionn Ferreira"
# The repo URL is deliberately NOT on the silkscreen - it will outlive the URL.
COPYRIGHT= "\u00a9 2026 Fionn Ferreira"

W, H = 187.0, 20.0
# rev I: the etched comb sensor is gone. A TTP223 module plugs into J4 instead, which
# deletes the pad section, the break-away, the bridges and the touch front end.
BX1, BX2, BY = 66.0, 130.0, 52.0          # electronics bulge, 64 x 32
# 15 LEDs at 11.13333 mm pitch. Fifteen at that spacing give a lit zone of exactly
# 167.00 mm - the lamp length stays put - while worst-case current drops to ~1.69 A,
# back under the 2 A PPTC hold and inside a 2.4 A supply. 20 LEDs needed neither.
NLED, PITCH = 15, 11.13333
# Centred on the strip: equal headroom both ends, so the lit row sits square.
LED_X = [(187.0 - (NLED-1)*PITCH)/2 + PITCH*i for i in range(NLED)]
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
# U1 moves aside so the USB-C can sit dead centre in the bulge. Its antenna keep-out
# then lands at y 40.9-46.3 facing the free y=52 edge, 23.9 mm from any LED copper.
put("U1","Espressif","ESP32-C3-MINI-1", 115.0, 38.0, 180, "ESP32-C3-MINI-1-N4")
put("J1","Connector_USB","USB_C_Receptacle_HRO_TYPE-C-31-M-12", 98.0, 49.0, 0, "USB-C 16P")

put("C1","Capacitor_SMD","CP_Elec_8x10", 73.0, 24.5, 0, "470uF/10V")
put("SW1","Button_Switch_SMD","SW_SPST_EVQP7C", 84.0, 23.5, 0, "BOOT")
put("F1","Resistor_SMD","R_1812_4532Metric", 92.0, 23.0, 0, "PPTC 2A/4A")
put("Q1","Package_TO_SOT_SMD","SOT-23", 99.0, 23.0, 0, "AO3401A")
put("R8",*R0402, 103.5, 22.4, 0, "100k"); put("C7",*C0402, 106.0, 22.4, 0, "100nF")
put("U3","Package_TO_SOT_SMD","SOT-23-5", 110.5, 23.0, 0, "AP2112K-3.3")
put("C2",*C0805, 115.0, 23.0, 0, "22uF"); put("C3",*C0805, 119.5, 23.0, 0, "22uF")
put("R9",*R0402, 89.0, 26.5, 0, "100k"); put("C8",*C0402, 91.5, 26.5, 0, "100nF")
# R10 was 4.7M for the etched sensor's discharge measurement. With a module doing the
# sensing it is only a pull-down, so it becomes 100k - which deletes the thinnest-stock
# line on the BOM.
put("R10",*R0402, 94.0, 26.5, 0, "100k"); put("R7",*R0402, 96.5, 26.5, 0, "5k1")

put("U2","Package_TO_SOT_SMD","SOT-23-5", 75.0, 31.0, 0, "SN74AHCT1G125")
put("C6",*C0402, 71.0, 31.0, 0, "100nF"); put("R11",*R0402, 78.5, 31.0, 0, "100R")
put("R3",*R0402, 75.0, 34.5, 0, "5k1"); put("C5",*C0805, 70.5, 34.5, 0, "22uF")
put("C4",*C0805, 84.0, 31.0, 0, "22uF"); put("C9",*C0402, 87.5, 31.0, 0, "100nF")
put("R4",*R0402, 90.0, 31.0, 0, "5k1"); put("R5",*R0402, 92.5, 31.0, 0, "5k1")
put("R6",*R0402, 95.0, 31.0, 0, "5k1")

put("U4","Package_TO_SOT_SMD","SOT-23-6", 86.0, 42.0, 0, "USBLC6-2SC6")
put("R1",*R0402, 89.0, 46.5, 0, "5k1"); put("R2",*R0402, 91.0, 46.5, 0, "5k1")
put("H1","MountingHole","MountingHole_2.7mm_M2.5", 126.0, 48.0, 0, "M2.5")
put("H2","MountingHole","MountingHole_2.7mm_M2.5", 126.0, 26.5, 0, "M2.5")
# A screw at each end of the LED strip, so the whole length is held, not just the bulge.
put("H3","MountingHole","MountingHole_2.7mm_M2.5", 6.0, 4.5, 0, "M2.5")
put("H4","MountingHole","MountingHole_2.7mm_M2.5", 181.0, 4.5, 0, "M2.5")

TP = {"TP1":("LED_5V",127.0,21.0),"TP2":("+3V3",122.0,27.0),"TP3":("GND",119.0,27.0),
      "TP4":("GND",116.0,27.0),"TP5":("LED_DIN1",79.5,20.9),"TP6":("TOUCH_SENSE",99.5,26.5),
      "TP7":("LD11_DOUT",178.0,18.6),"TP8":("UART_TX",104.0,31.0),"TP9":("UART_RX",101.0,31.0),
      "TP10":("EN",100.0,18.5),"TP11":("VBUS_F",87.5,18.8)}
for ref,(net,x,y) in TP.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", x, y, 0, net)
    for p in fp.Pads(): p.SetNet(N(net))
JST3 = ("Connector_JST","JST_PH_S3B-PH-SM4-TB_1x03-1MP_P2.00mm_Horizontal")
# J4: a TTP223-class module plugs straight in, pin order IO / VCC / GND.
# VCC is 3V3 and not 5V on purpose - these modules drive their output rail-to-rail and
# the ESP32-C3 is not 5V tolerant (3.6 V absolute max). At 3V3 the output is safe, and
# R7's 5.1 k stays in series as belt and braces.
fp = put("J4", *JST3, 78.0, 46.0, 0, "IO/VCC/GND")
for pd in fp.Pads():
    pd.SetNet(N({"1":"TOUCH_SENSE","2":"+3V3","3":"GND"}.get(pd.GetNumber(),"GND")))

# Same order in solder terminals, for when no JST housing is to hand.
for ref,(xx,yy,net) in {"TS3":(99.0,35.5,"TOUCH_SENSE"), "TS4":(102.0,35.5,"+3V3"),
                        "TS5":(105.0,35.5,"GND")}.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", xx, yy, 0, net)
    for pd in fp.Pads(): pd.SetNet(N(net))

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

# Outline: strip plus bulge. No pad section, no break line.
for a in [(0,0,W,0),(W,0,W,H),(W,H,BX2,H),(BX2,H,BX2,BY),(BX2,BY,BX1,BY),
          (BX1,BY,BX1,H),(BX1,H,0,H),(0,H,0,0)]:
    seg(*a)

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
silk("EMBER", 150.0, 17.7, 1.6, 0.26)
silk(f"EM-15 {VERSION}   \u00b7   {COPYRIGHT}", 150.0, 19.0, 0.8, 0.15)
silk("EMBER", 96.0, 51.0, 0.8, 0.15)
silk("TTP223  IO VCC GND", 102.0, 37.6, 0.8, 0.15)

pcbnew.SaveBoard(OUT, board)
print("PLACED:", len(placed), " NETS:", len(nets),
      " UNMATCHED:", unmatched if unmatched else "none")
