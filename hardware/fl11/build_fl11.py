# FL-11 board generator. Coordinates are the §7 values; y runs from the y=0 long edge.
import os, sys, json
import pcbnew
from pcbnew import VECTOR2I, FromMM as MM

OUT = sys.argv[1]
KI  = os.path.expanduser("~/Applications/KiCad.app/Contents/SharedSupport/footprints")
ESP = sys.argv[2]

W, H = 282.0, 20.0
LED_X = [64.000,80.667,97.333,114.000,130.667,147.333,164.000,180.667,197.333,214.000,230.667]
LED_Y = 11.000
SLOT_X = 250.0

board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.SetBoardThickness(MM(1.6))

nets = {}
def N(name):
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni); nets[name] = ni
    return nets[name]

for n in ["GND","VBUS_RAW","VBUS_F","+5V","LED_5V","+3V3","GATE","EN","CC1","CC2",
          "USB_DP_CONN","USB_DM_CONN","USB_DP","USB_DM","LED_DATA_3V3","LED_DATA_5V",
          "LED_DIN1","LD11_DOUT","TOUCH_GPIO","TOUCH_SENSE","BOOT_N","STRAP2","STRAP8",
          "UART_TX","UART_RX"]:
    N(n)
for i in range(1,11):
    N(f"D_{i}_{i+1}")

placed = {}
def put(ref, lib, fpname, x, y, rot=0, value=""):
    path = ESP if lib == "Espressif" else f"{KI}/{lib}.pretty"
    fp = pcbnew.FootprintLoad(path, fpname)
    if fp is None:
        raise SystemExit(f"MISSING FOOTPRINT {lib}:{fpname}")
    fp.SetPosition(VECTOR2I(MM(x), MM(y)))
    if rot: fp.SetOrientationDegrees(rot)
    fp.SetReference(ref); fp.SetValue(value or ref)
    board.Add(fp); placed[ref] = fp
    return fp

R0402 = ("Resistor_SMD","R_0402_1005Metric")
C0402 = ("Capacitor_SMD","C_0402_1005Metric")
C0805 = ("Capacitor_SMD","C_0805_2012Metric")

# ── Step 2: the LED row. Every other dimension derives from it.
for i, x in enumerate(LED_X, start=1):
    put(f"LD{i}", "LED_SMD", "LED_WS2812B_PLCC4_5.0x5.0mm_P3.2mm", x, LED_Y, 90, "SK6812RGBW")
    put(f"C{9+i}", *C0402, x + 3.40, 15.50, 90, "100nF")

# ── Step 4/5: module (antenna end at y=0), USB-C at x=0, mounting holes
put("U1","Espressif","ESP32-C3-MINI-1", 44.0, 8.9, 0, "ESP32-C3-MINI-1-N4")
put("J1","Connector_USB","USB_C_Receptacle_HRO_TYPE-C-31-M-12", 6.0, 10.0, 90, "USB-C 16P")
# H1/H2 moved from the doc's (4.50, 4.50/15.50) to x=12.0. A real 16-pin receptacle's
# courtyard is x 0.69-10.20, y 4.63-15.37, and an M2.5 screw head (6 mm courtyard) does
# not fit beside it on a 20 mm board. Moved behind the connector instead: the axial
# cable-yank load still passes into the screws, which was the point.
put("H1","MountingHole","MountingHole_2.7mm_M2.5", 13.5, 2.1, 0, "M2.5")
put("H2","MountingHole","MountingHole_2.7mm_M2.5", 13.5, 17.9, 0, "M2.5")

# ── Step 6: input path. Two hard constraints shape this: U1's courtyard occupies
# x 37.16-50.84 for y 0.35-17.45, and J1's is x 0.69-10.20, y 4.63-15.37.
put("F1","Resistor_SMD","R_1812_4532Metric", 20.0, 2.6, 0, "PPTC 2A/4A")
put("U4","Package_TO_SOT_SMD","SOT-23-6", 19.0, 17.5, 0, "USBLC6-2SC6")
put("R1",*R0402, 3.5, 18.6, 0, "5k1"); put("R2",*R0402, 5.8, 18.6, 0, "5k1")
put("C1","Capacitor_SMD","CP_Elec_8x10", 24.0, 10.2, 90, "470uF/10V")
put("Q1","Package_TO_SOT_SMD","SOT-23", 30.5, 2.8, 0, "AO3401A")
put("R8",*R0402, 35.5, 2.2, 0, "100k"); put("C7",*C0402, 35.5, 4.0, 0, "100nF")
put("SW1","Button_Switch_SMD","SW_SPST_EVQP7C", 24.5, 17.6, 0, "BOOT")
# LDO cluster sits right of C1 and left of U1 - the only pocket that fits it with
# C2/C3 within 3 mm of the regulator, which is what the stability spec requires.
put("U3","Package_TO_SOT_SMD","SOT-23-5", 33.0, 9.0, 0, "AP2112K-3.3")
put("C2",*C0805, 33.0, 12.5, 0, "22uF"); put("C3",*C0805, 33.0, 5.8, 0, "22uF")
put("R9",*R0402, 28.7, 17.6, 0, "100k"); put("C8",*C0402, 31.0, 17.6, 0, "100nF")

# ── Step 7: buffer cluster, clear of the antenna region and of U1's courtyard
put("U2","Package_TO_SOT_SMD","SOT-23-5", 55.5, 13.5, 0, "SN74AHCT1G125")
put("C6",*C0402, 51.9, 13.5, 0, "100nF"); put("R11",*R0402, 58.5, 13.5, 0, "47R")
put("R3",*R0402, 57.5, 16.8, 0, "5k1"); put("C5",*C0805, 53.9, 17.0, 0, "22uF")
put("C4",*C0805, 53.0, 8.0, 0, "22uF"); put("C9",*C0402, 52.5, 10.2, 0, "100nF")

# ── Step 8: touch front end
put("R10",*R0402, 53.5, 3.6, 0, "4M7"); put("R7",*R0402, 56.0, 3.6, 0, "5k1")

# straps - must sit below U1's courtyard (y > 17.45)
put("R4",*R0402, 41.5, 18.7, 0, "5k1"); put("R5",*R0402, 44.0, 18.7, 0, "5k1")
put("R6",*R0402, 46.5, 18.7, 0, "5k1")

# ── Test points and the rewire pads (J2 main side, J3 tab side)
TP = {"TP1":("LED_5V",59.0,15.5),"TP2":("+3V3",49.0,18.7),"TP3":("GND",51.3,18.7),
      "TP4":("GND",246.0,17.5),"TP5":("LED_DIN1",59.0,7.0),"TP6":("TOUCH_SENSE",58.6,3.6),
      "TP7":("LD11_DOUT",240.0,13.0),"TP8":("UART_TX",35.8,12.5),"TP9":("UART_RX",35.2,15.0),
      "TP10":("EN",29.5,12.5),"TP11":("VBUS_F",16.0,7.5)}
for ref,(net,x,y) in TP.items():
    fp = put(ref,"TestPoint","TestPoint_Pad_D1.0mm", x, y, 0, net)
    for p in fp.Pads(): p.SetNet(N(net))

for ref, x in (("J2",245.0),("J3",254.0)):
    for idx,(yy,net) in enumerate(((8.73,"TOUCH_SENSE"),(11.27,"GND")), start=1):
        fp = put(f"{ref}_{idx}","TestPoint","TestPoint_Pad_D1.0mm", x, yy, 0, net)
        for p in fp.Pads(): p.SetNet(N(net))

# ── Net assignment by (ref, pad)
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
# Module pads: authoritative map from Espressif's own symbol, not invented.
PAD = json.load(open(sys.argv[3]))
for sig, net in (("IO5","LED_DATA_3V3"),("IO3","TOUCH_GPIO"),("IO2","STRAP2"),
                 ("IO8","STRAP8"),("IO9","BOOT_N"),("IO18","USB_DM"),("IO19","USB_DP"),
                 ("IO20","UART_RX"),("IO21","UART_TX"),("EN","EN"),("3V3","+3V3")):
    CONN[("U1", PAD[sig])] = net
for g in PAD["GND"]:
    CONN[("U1", g)] = "GND"

# LEDs: 1=VDD 2=DOUT 3=VSS 4=DIN
for i in range(1,12):
    CONN[(f"LD{i}","1")] = "LED_5V"
    CONN[(f"LD{i}","3")] = "GND"
    CONN[(f"LD{i}","2")] = f"D_{i}_{i+1}" if i < 11 else "LD11_DOUT"
    CONN[(f"LD{i}","4")] = "LED_DIN1" if i == 1 else f"D_{i-1}_{i}"
    CONN[(f"C{9+i}","1")] = "LED_5V"
    CONN[(f"C{9+i}","2")] = "GND"

# USB-C by pad name
for pad, net in (("A1","GND"),("B1","GND"),("A12","GND"),("B12","GND"),
                 ("A4","VBUS_RAW"),("B4","VBUS_RAW"),("A9","VBUS_RAW"),("B9","VBUS_RAW"),
                 ("A5","CC1"),("B5","CC2"),
                 ("A6","USB_DP_CONN"),("B6","USB_DP_CONN"),
                 ("A7","USB_DM_CONN"),("B7","USB_DM_CONN"),
                 ("SH","GND")):
    CONN[("J1",pad)] = net

unmatched = []
for (ref,padnum), net in CONN.items():
    fp = placed.get(ref)
    if fp is None: unmatched.append((ref,padnum,"NO FOOTPRINT")); continue
    hit = False
    for p in fp.Pads():
        if p.GetNumber() == padnum:
            p.SetNet(N(net)); hit = True
    if not hit: unmatched.append((ref,padnum,net))

# ── Step 1: outline, break slot, mouse bites
def seg(x1,y1,x2,y2,layer=pcbnew.Edge_Cuts,width=0.1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(VECTOR2I(MM(x1),MM(y1))); s.SetEnd(VECTOR2I(MM(x2),MM(y2)))
    s.SetLayer(layer); s.SetWidth(MM(width)); board.Add(s); return s

for a in [(0,0,W,0),(W,0,W,H),(W,H,0,H),(0,H,0,0)]: seg(*a)
# Break slot: two routed segments leaving mouse-bite webs
# Webs sit exactly where SENSE and GND cross the break line - that is what the
# doc calls the centre bridge. Wider there so a 0.30 mm trace keeps clearance.
BITES = [(3.0,0.7),(8.73,1.8),(11.27,1.8),(16.5,0.7)]
edges = [0.35]
for cy,w in BITES: edges += [cy-w/2, cy+w/2]
edges.append(H - 0.35)
for i in range(0,len(edges),2):
    y1,y2 = edges[i], edges[i+1]
    if y2 - y1 > 0.05:
        seg(SLOT_X-0.4, y1, SLOT_X-0.4, y2); seg(SLOT_X+0.4, y1, SLOT_X+0.4, y2)
        seg(SLOT_X-0.4, y1, SLOT_X+0.4, y1); seg(SLOT_X-0.4, y2, SLOT_X+0.4, y2)

pcbnew.SaveBoard(OUT, board)
print("PLACED:", len(placed), "footprints")
print("NETS:", len(nets))
if unmatched:
    print("UNMATCHED PADS:", len(unmatched))
    for u in unmatched[:15]: print("   ", u)
else:
    print("UNMATCHED PADS: none")
