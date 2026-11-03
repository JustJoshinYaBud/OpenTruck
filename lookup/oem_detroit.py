"""OpenTruck - Detroit Diesel DD13/DD15/DD16 fault-code table (STARTER SET).

SPN+FMI -> short description. THIS IS A STARTER SET, NOT THE COMPLETE LIST:
Detroit's codes are published one procedure at a time, so - unlike a maker
with a single full DTC list - each additional code has to be found and
extracted separately from public sources. Grow the table the same way.

DISCLAIMER: The data in this file is a compilation assembled from sources
found through ordinary internet search (public service documentation,
fault-code lists and similar material). It is not an official publication
of Detroit Diesel Corporation, and the OpenTruck project has no affiliation with, sponsorship
from, or endorsement by Detroit Diesel Corporation or any vehicle, engine or component
manufacturer; all brand names are the property of their respective owners.
The contents may be inaccurate, incomplete or out of date and are provided
as-is, without warranty of any kind."""

# (spn, fmi) -> description
DETROIT_SPN_FMI: dict[tuple[int, int], str] = {
    # --- aftertreatment -------------------------------------------------------
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
    # --- per-SPN diagnostic procedures ----------------------------------------
    (100, 0): "Oil Pressure Stuck",
    (100, 1): "Low Engine Oil Pressure",
    (100, 10): "Low Oil Pressure Derate",
    (3563, 18): "Inlet Manifold Pressure Low",
    (2791, 10): "Exhaust Gas Recirculation Actuator Slow Response",
    (3464, 18): "Intake Manifold Pressure Too Low During Regeneration (Restricted Mode)",
    (1077, 14): "Leakage in High Pressure Fuel System Too High (Leak Down Test)",
    (157, 1): "Rail Pressure Too High",
    (157, 10): "Under-Capacity in the High Pressure Circuit",
    (157, 18): "Fuel Rail Pressure High",
    (411, 1): "EGR Differential Pressure Failed (High Box)",
    # --- additional per-SPN procedures -----------------------------------------
    (3361, 5): "DEF System Circuit Failed Open",
    (520296, 31): "EGR Valve Actuator, Learn Cycle Incomplete",
    (521012, 1): "Intake Manifold Pressure Too Low (Fault Reaction Manager)",
    (1323, 31): "Idle Smoothness Control / Cylinder 1 Misfire at Idle",
    (1324, 31): "Idle Smoothness Control / Cylinder 2 Misfire at Idle",
    (1325, 31): "Idle Smoothness Control / Cylinder 3 Misfire at Idle",
    (1326, 31): "Idle Smoothness Control / Cylinder 4 Misfire at Idle",
    (1327, 31): "Idle Smoothness Control / Cylinder 5 Misfire at Idle",
    (1328, 31): "Idle Smoothness Control / Cylinder 6 Misfire at Idle",
    (636, 2): "No Match of Camshaft and Crankshaft Signals",
    (723, 31): "Reverse Engine Rotation Detected",
}