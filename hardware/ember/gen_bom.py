#!/usr/bin/env python3
"""Regenerate ember-bom.csv / ember-cpl.csv from a kicad-cli position export.

LCSC numbers rechecked against live JLCPCB stock and the is_basic flag on 2026-08-20.
BASIC parts carry no feeder fee and no MOQ, which is why they are preferred here even
where an Extended part is nominally cheaper. STOCK MOVES - re-verify before ordering.
"""
import csv, collections, re, subprocess, sys, os

PART = {
 "100nF":      ("C1525",     "BASIC. 16.4M stock, 16V X7R"),
 "22uF":       ("C6119897",  "0805 10V X5R, 184k stock, $0.020 vs $0.119 for the 25V BASIC part C45783 - the single biggest safe saving on the board, $0.39/unit across four places. DC bias at 5V derates it to ~10-12uF effective, which is fine here: the LDO needs >=1uF, and C1's 470uF carries the bulk"),
 "5k1":        ("C25905",    "BASIC. 8.4M stock, 1%"),
 "100k":       ("C25741",    "BASIC. 15.4M stock, 1%. Replaces C25086 - JLC now lists that Extended, 0 stock, MOQ 700"),
 "100R":       ("C25076",    "BASIC. 9.8M stock"),
 
 "470uF/10V":  ("C47023096", "Extended. 7.4k stock, D8 x 10.5mm - thinnest stock on the board after the LED"),
 "IO/VCC/GND": ("C7429690",  "ZX-PH2.0-WT3P, 3-pin 2.0mm right-angle SMD, 17k stock, $0.053. Genuine JST S3B-PH-SM4-TB is C265101 at $0.377 if the clone footprint disappoints - CHECK the chosen part's drawing against the JST land pattern before ordering"),
 "PPTC 2A/4A": ("C883156",   "Extended. BSMD1812-200-16V, 2A hold / 4A trip, 76k stock - the section 6.2 spec. At 15 LEDs worst case is ~1.69 A"),
 "USBLC6-2SC6":("C2687116",  "Extended. 150k stock"),
 "AP2112K-3.3":("C23380830", "Extended. 31k stock. EN ties to VIN, not VOUT"),
 "BOOT":       ("C49234124", "3x4x2mm SMD tact, 101k stock, $0.019 - half the price of C18078117 with 5x the stock"),
 "ESP32-C3-MINI-1-N4": ("C2838502","Extended. 26k stock, $3.84 - doc modelled $2.92, budget ~$0.9/board more"),
 "SN74AHCT1G125": ("C7484",  "AHCT/HCT ONLY. C7468 is AHC and fixes nothing - two digits apart"),
 "AO3401A":    ("C15127",    "P-FET. Source to INPUT side, drain to load"),
 "USB-C 16P":  ("C165948",   "HRO TYPE-C-31-M-12, 90k stock, $0.186. The $0.087 GT-USB-7010ASV was rejected: its footprint has 0.175 mm copper-to-hole, under JLC's 0.25 mm minimum. TOP side, plug enters from the rear board edge"),
 "SK6812RGBW": ("C5378724",  "SKC6812RGBW-WS = WARM WHITE (the -NW suffix, C5348912, is neutral and would fight BASE_WARM_WHITE). *** STOCK NOT VERIFIED - section 9.1 number one live risk. 4-channel RGBW, GRBW order. An RGB part fits the same footprint and is silently wrong ***"),
}

CLI = os.path.expanduser("~/Applications/KiCad.app/Contents/MacOS/kicad-cli")
here = os.path.dirname(os.path.abspath(__file__))
raw  = os.path.join(here, "cpl-raw.csv")
subprocess.run([CLI,"pcb","export","pos","--format","csv","--units","mm","--side","both",
                "--use-drill-file-origin","-o",raw,os.path.join(here,"ember.kicad_pcb")],
               check=True, capture_output=True)
rows=[r for r in csv.DictReader(open(raw))]
skip=lambda r: r["Ref"].startswith(("TP","H","J2_","J3_"))
with open(os.path.join(here,"ember-cpl.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["Designator","Mid X","Mid Y","Layer","Rotation"])
    for r in rows:
        if not skip(r):
            w.writerow([r["Ref"],f'{float(r["PosX"]):.4f}',f'{float(r["PosY"]):.4f}',
                        "Top" if r["Side"]=="top" else "Bottom",f'{float(r["Rot"]):.1f}'])
g=collections.OrderedDict()
for r in rows:
    if not skip(r): g.setdefault((r["Val"],r["Package"]),[]).append(r["Ref"])
key=lambda s:(re.match(r"([A-Za-z]+)(\d+)",s).group(1),int(re.match(r"([A-Za-z]+)(\d+)",s).group(2)))
missing=[]
with open(os.path.join(here,"ember-bom.csv"),"w",newline="") as f:
    w=csv.writer(f); w.writerow(["Comment","Designator","Footprint","LCSC Part #","Note"])
    for (val,pkg),refs in g.items():
        c,note=PART.get(val,("",""))
        if not c: missing.append(val)
        w.writerow([val,",".join(sorted(refs,key=key)),pkg,c,note])
os.remove(raw)
bottom=[r["Ref"] for r in rows if not skip(r) and r["Side"]!="top"]
basic=sum(1 for v,_ in g if PART.get(v,("",""))[1].startswith("BASIC"))
print(f"BOM lines {len(g)}  placements {sum(1 for r in rows if not skip(r))}  "
      f"BASIC lines {basic}  bottom-side {bottom or 'NONE (single-sided)'}")
if missing: print("MISSING C-NUMBERS:", missing)
