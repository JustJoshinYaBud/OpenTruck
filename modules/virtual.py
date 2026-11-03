"""OpenTruck - virtual (computed) live-data parameters.

These values are not broadcast by the vehicle; they are calculated from two or
more real parameters we already decode. ``compute_live(mapping)`` takes a merged
``{name: (value, unit)}`` view (first match across modules) and returns the
derived parameters to attach to the engine module:

  * Fuel Economy (instant) - fuel rate (L/h) / road speed (km/h)  -> L/100km
  * Fuel Economy (avg)     - fuel used (L) / distance (km)        -> L/100km
  * Boost (gauge)          - intake-manifold pressure - barometric -> kPa
  * Engine Torque (calc)   - actual torque % x engine reference torque -> Nm
  * Engine Power (calc)    - torque (Nm) x engine speed (rpm)     -> kW
  * Derate %               - driver demand torque % - actual %    -> %

Idle % and average road speed are aggregates, so they are computed in the Totals
panel (``app._totals_rows``) instead of here.

Values are emitted in canonical metric/imperial-neutral units so the shared
``units.convert`` display converter applies; ``units.py`` special-cases fuel
economy (inverse scaling) and adds kW -> hp.
"""
from __future__ import annotations


def _val(mapping: dict, name: str):
    """Float value of ``mapping[name]`` (dropping the unit), or None."""
    try:
        return float(str(mapping[name][0]).replace(",", ""))
    except (KeyError, TypeError, ValueError):
        return None


def _first(mapping: dict, *names: str):
    for n in names:
        if n in mapping:
            return n
    return None


def compute_live(live: dict) -> dict:
    """Return derived parameters ``{name: (value_str, unit)}``."""
    out: dict[str, tuple[str, str]] = {}

    # --- Instantaneous fuel economy (L/100km) ------------------------------ #
    fr = _first(live, "Engine Fuel Rate", "Fuel Rate (Instantaneous)")
    sp = _first(live, "Wheel-Based Vehicle Speed", "Road Speed")
    if fr and sp:
        f, s = _val(live, fr), _val(live, sp)
        if f is not None and s is not None and s > 0.5 and f >= 0:
            out["Fuel Economy (instant)"] = (f"{f / s * 100.0:.1f}", "L/100km")

    # --- Average fuel economy (L/100km) ------------------------------------ #
    di = _first(live, "Trip Distance", "Total Vehicle Distance")
    fu = _first(live, "Trip Fuel", "Total Fuel Used")
    if di and fu:
        d, f = _val(live, di), _val(live, fu)
        if d and f is not None and f >= 0:
            out["Fuel Economy (avg)"] = (f"{f / d * 100.0:.1f}", "L/100km")

    # --- Boost (gauge) ------------------------------------------------------ #
    # Prefer the parameter the ECM ITSELF calls "Boost Pressure" (J1587 PID 102).
    # It is a GAUGE value (reads 0 kPa with the engine off), so it needs no
    # barometric offset applied.
    #
    # Only fall back to computing manifold-absolute minus barometric, and only
    # when the manifold reading is physically plausible. An absolute intake
    # pressure cannot be near zero, but at least one ECM does not populate
    # IC1's SPN 102 field (reading 0 kPa with the engine off), and subtracting
    # full barometric from that produced a bogus
    # "-14.2 psi" boost gauge.
    bo = _first(live, "Boost Pressure")
    if bo:
        b = _val(live, bo)
        if b is not None:
            out["Boost (gauge)"] = (f"{b:.1f}", "kPa")
    if "Boost (gauge)" not in out:
        mp = _first(live, "Intake Manifold Pressure")
        bp = _first(live, "Barometric Pressure")
        if mp and bp:
            m, b = _val(live, mp), _val(live, bp)
            if m is not None and b is not None and m >= 50.0:
                out["Boost (gauge)"] = (f"{m - b:.1f}", "kPa")

    # --- Engine torque (Nm) and power (kW) --------------------------------- #
    tp = _first(live, "Actual Engine Torque")
    rt = _first(live, "Engine Reference Torque")
    torque_nm = None
    if tp and rt:
        t, r = _val(live, tp), _val(live, rt)
        if t is not None and r is not None:
            torque_nm = t / 100.0 * r
            out["Engine Torque (calc)"] = (f"{torque_nm:.0f}", "Nm")
    rpm_name = _first(live, "Engine Speed")
    if torque_nm is not None and rpm_name:
        rpm = _val(live, rpm_name)
        if rpm is not None:
            # P(kW) = torque(Nm) * speed(rpm) / 9549.3
            out["Engine Power (calc)"] = (f"{torque_nm * rpm / 9549.3:.0f}", "kW")

    # --- Derate % = driver demand torque - actual torque (clamped >= 0) ----- #
    # When the engine is not derated the ECU meets the demanded torque, so
    # actual >= demand and this reads 0. A derate shows as the shortfall in %.
    dd = _first(live, "Driver Demand Torque")
    at = _first(live, "Actual Engine Torque")
    if dd and at:
        demand = _val(live, dd)
        actual = _val(live, at)
        if demand is not None and actual is not None:
            out["Derate %"] = (f"{max(0.0, demand - actual):.0f}", "%")

    return out
