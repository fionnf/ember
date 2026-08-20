#!/usr/bin/env python3
"""Regenerate fl11-bom.csv / fl11-cpl.csv from a kicad-cli position export.

LCSC numbers rechecked against live JLCPCB stock and the is_basic flag on 2026-08-20.
BASIC parts carry no feeder fee and no MOQ, which is why they are preferred here even
where an Extended part is nominally cheaper. STOCK MOVES - re-verify before ordering.
"""
import csv, collections, re, subprocess, sys, os

PART = {
 "100nF":      ("C1525",     "BASIC. 16.4M stock, 16V X7R"),
 "22uF":       ("C45783",    "BASIC. 1.73M stock, 0805 25V X5R. Cheaper Extended alt C6119897 (10V, $0.02 vs $0.12) carries a feeder fee and derates to ~10uF at 5V"),
 "5k1":        ("C25905",    "BASIC. 8.4M stock, 1%"),
 "100k":       ("C25741",    "BASIC. 15.4M stock, 1%. Replaces C25086 - JLC now lists that Extended, 0 stock, MOQ 700"),
 "100R":       ("C25076",    "BASIC. 9.8M stock"),
 "4M7":        ("C474132",   "Extended - no BASIC 4.7M exists in 0402. 389k stock. Replaces C49655641 (9.8k). Do NOT drop to 1M"),
 "470uF/10V":  ("C47023096", "Extended. 7.4k stock, D8 x 10.5mm - thinnest stock on the board after the LED"),
 "PPTC 2A/4A": ("C883156",   "Extended. BSMD1812-200-16V, 2A hold / 4A trip, 76k stock - exactly the section 6.2 spec"),
 "USBLC6-2SC6":("C2687116",  "Extended. 150k stock"),
 "AP2112K-3.3":("C23380830", "Extended. 31k stock. EN ties to VIN, not VOUT"),
 "BOOT":       ("C18078117", "Extended. 20.5k stock, 3x4mm SMD tact"),
 "ESP32-C3-MINI-1-N4": ("C2838502","Extended. 26k stock, $3.84 - doc modelled $2.92, budget ~$0.9/board more"),
 "SN74AHCT1G125": ("C7484",  "AHCT/HCT ONLY. C7468 is AHC and fixes nothing - two digits apart"),
 "AO3401A":    ("C15127",    "P-FET. Source to INPUT side, drain to load"),
 "USB-C 16P":  ("C165948",   "TOP side, horizontal - plug enters from the rear board edge"),
 "SK6812RGBW": ("C5378724",  "*** STOCK NOT VERIFIED - section 9.1 number one live risk. 4-channel RGBW, GRBW order. An RGB part fits the same footprint and is silently wrong ***"),
}

CLI = os.path.expanduser("~/Applications/KiCad.app/Contents/MacOS/kicad-cli")
here = os.path.dirname(os.path.abspath(__file__))
raw  = os.path.join(here, "cpl-raw.csv")
subprocess.run([CLI,"pcb","export","pos","--format","csv","--units","mm","--side","both",
                "--use-drill-file-origin","-o",raw,os.path.join(here,"fl11.kicad_pcb")],
               check=True, capture_output=True)
rows=[r for r in csv.DictReader(open(raw))]
skip=lambda r: r["Ref"].startswith(("TP","H","J2_","J3_"))
with open(os.path.join(here,"fl11-cpl.csv"),"w",newline="") as f:
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
with open(os.path.join(here,"fl11-bom.csv"),"w",newline="") as f:
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
