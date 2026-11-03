"""OpenTruck - Detroit Diesel DD13/DD15/DD16 fault-code table (STARTER SET).

SPN+FMI -> short description, harvested from **official Detroit Diesel
documents** published by Detroit Diesel Corporation and mirrored by NHTSA at
``static.nhtsa.gov`` (their per-SPN diagnostic procedure extracts from
``DDC-SVC-MAN-0084`` / ``DDC-SVC-MAN-0191`` / ``DDC-SVC-MAN-0208``, plus the
Heavy Duty Aftertreatment Failure Guide). Each entry below cites the document it
came from, so it can be re-verified.

THIS IS A STARTER SET, NOT THE COMPLETE LIST. Detroit's diagnostic procedures are
published **one SPN/FMI at a time**, so unlike Navistar (one document holding a
full DTC list) each additional code requires finding and extracting another
NHTSA-hosted document. Grow this table by harvesting more of those documents -
the descriptions below are exactly the "Table 1. SPN x/FMI y - <title>" headers
of the source procedures.

Only short factual descriptions are kept; no troubleshooting prose is
redistributed. Resolution goes through ``oem.resolve_code_description`` (OEM
override first, then the generic SAE name), so these apply ONLY to a module
identified as Detroit Diesel and never leak into another maker's engine.

NOTE: the 520xxx / 524xxx SPNs seen in the field (MCM Software Reset, Missing
VIN, MCM Hardware, soot-sensor heater faults, Predictive Cruise Control) live in
SAE's manufacturer-reserved band and are NOT yet covered - those need their own
documents harvested.
"""

# (spn, fmi) -> description
DETROIT_SPN_FMI: dict[tuple[int, int], str] = {
    # --- aftertreatment (Heavy Duty Aftertreatment Failure Guide, DDC-SVC-MAN-0208,
    #     "Codes of Interest for ATS Failure or Plugging", MC-10151579) ----------
    (3246, 0): "Diesel Particulate Filter Outlet Temperature - Very High",
    (3246, 15): "Diesel Particulate Filter Outlet Temperature - High",
    (4363, 0): "Selective Catalyst Reduction Outlet Temperature High",
    (3250, 0): "Diesel Oxidation Catalyst Outlet Temperature Very High",
    (3250, 15): "Diesel Oxidation Catalyst Outlet Temperature High",
    (3556, 0): "Regeneration Temperature - Out of Range High",
    (3556, 1): "Regeneration Temperature - Out Of Range Low",
    (2631, 1): "Low Air Flow",
    (3556, 18): "Diesel Oxidation Catalyst Outlet Temperature Low (Low Temp Regeneration)",
    (3251, 0): "Diesel Particulate Filter Pressure Out of Range Very High",
    (3251, 16): "Diesel Particulate Filter Pressure Out of Range High",
    (3251, 20): "Diesel Oxidation Catalyst Inlet Pressure - Not Plausible",
    (3251, 2): "Diesel Oxidation Catalyst (DOC) Inlet Pressure - Not Plausible",
    (102, 18): "Intake Manifold Pressure Too Low",
    (2659, 0): "Exhaust Gas Recirculation Flow Target Error Diagnostic - High Flow",
    (3720, 15): "DPF Ash Clean Request",
    # --- per-SPN diagnostic procedures (DDC-SVC-MAN-0084 / 0191) -------------
    (100, 0): "Oil Pressure Stuck",                       # SB-10083161 (GHG17)
    (100, 1): "Low Engine Oil Pressure",                  # SB-10083161
    (100, 10): "Low Oil Pressure Derate",                 # SB-10083161 (GHG17)
    (3563, 18): "Inlet Manifold Pressure Low",            # MC-10146326 (EPA07/10/GHG14)
    (2791, 10): "Exhaust Gas Recirculation Actuator Slow Response",  # MC-10133566
    (3464, 18): "Intake Manifold Pressure Too Low During Regeneration (Restricted Mode)",  # MC-10142099
    (1077, 14): "Leakage in High Pressure Fuel System Too High (Leak Down Test)",  # MC-10133579
    (157, 1): "Rail Pressure Too High",                   # MC-10142009 (GHG14)
    (157, 10): "Under-Capacity in the High Pressure Circuit",  # MC-10142009
    (157, 18): "Fuel Rail Pressure High",                 # MC-10142009 (EPA10/GHG14)
    (411, 1): "EGR Differential Pressure Failed (High Box)",  # MC-10119529 (EPA10/GHG14)
    # --- additional per-SPN procedures (official, NHTSA-mirrored) ----------
    (3361, 5): "DEF System Circuit Failed Open",                    # MC-10133588 (GHG14/17)
    (520296, 31): "EGR Valve Actuator, Learn Cycle Incomplete",     # MC-10133560 (GHG14/17)
    (521012, 1): "Intake Manifold Pressure Too Low (Fault Reaction Manager)",  # MC-10142128 (DD5)
    (1323, 31): "Idle Smoothness Control / Cylinder 1 Misfire at Idle",  # MC-10142319 (GHG14)
    (1324, 31): "Idle Smoothness Control / Cylinder 2 Misfire at Idle",  # MC-10142319
    (1325, 31): "Idle Smoothness Control / Cylinder 3 Misfire at Idle",  # MC-10142319
    (1326, 31): "Idle Smoothness Control / Cylinder 4 Misfire at Idle",  # MC-10142319
    (1327, 31): "Idle Smoothness Control / Cylinder 5 Misfire at Idle",  # MC-10142319
    (1328, 31): "Idle Smoothness Control / Cylinder 6 Misfire at Idle",  # MC-10142319
    (636, 2): "No Match of Camshaft and Crankshaft Signals",        # MC-10129671
    (723, 31): "Reverse Engine Rotation Detected",                  # MC-10129671
}