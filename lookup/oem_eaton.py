"""OpenTruck - Eaton Fuller "Top 2" transmission fault overlay.

The Fuller Top-2 splitter/lockout system has **no controller of its own**: the
ENGINE ECM drives the solenoids and reports the resulting faults under its own
MID, using transmission-flavoured SIDs and PIDs. So on such a truck a
transmission fault genuinely arrives as, for example, ``SID 40 FMI 4`` from the
engine module.

That collides with the SAE engine-class meaning of the same numbers (SID 40 on
an engine is "Auxiliary Output Device Driver #2"), which is why these entries
live in an overlay rather than in the per-maker tables:

  * it is applied ONLY to engine-class MIDs, and
  * ONLY when a transmission module is also present on the bus (MID 130/176 on
    J1587, or a J1939 module whose function/CI says transmission). Without a
    gearbox in sight, the engine's own SID meaning wins.
  * the rendered description always starts with "Transmission (Eaton Fuller
    Top-2): ", so a code shown under the Engine module is unmistakable.

Source: Eaton Fuller Transmissions Troubleshooting Guide **TRTS-0070**
(official Eaton publication, eaton.com). Only the short component/condition
names are stored; its procedures are not redistributed.

Deliberately NOT included: the Mack row (SID 10/11 FMI 3/4). On an engine MID
SID 10/11 are "Injector Cylinder #10/#11" - a real and common engine fault -
so relabelling them as transmission faults would be worse than the alternative.
"""

from __future__ import annotations

from typing import Optional

_PREFIX = "Transmission (Eaton Fuller Top-2): "

# (SID, FMI) -> short description, exactly the pairs listed in TRTS-0070.
EATON_SID_FMI: dict[tuple[int, int], str] = {
    # DDEC III: shift solenoid / lockout solenoid, electrical
    (26, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (26, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (40, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (40, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (53, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (53, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (54, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (54, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (55, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (55, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    (56, 3): "Shift Solenoid or Lockout Solenoid - open circuit",
    (56, 4): "Shift Solenoid or Lockout Solenoid - shorted circuit",
    # Caterpillar: shift / lockout solenoid, electrical
    (40, 5): "Shift Solenoid or Lockout Solenoid - current below normal",
    (40, 6): "Shift Solenoid or Lockout Solenoid - current above normal",
    (51, 5): "Lockout Solenoid - current below normal",
    (51, 6): "Lockout Solenoid - current above normal",
    # Cummins: lockout solenoid / mechanical
    (40, 11): "Lockout Solenoid - mechanical system not responding",
    (51, 11): "Shift Solenoid or Lockout Solenoid - mechanical system not responding",
    # DDEC III: failed to complete the commanded split shift
    (26, 7): "Mechanical system not responding (shift not completed)",
    (40, 7): "Mechanical system not responding (shift not completed)",
}

# PID-based evidence of the same system (transmission output shaft speed not
# responding = the commanded shift did not take place).
EATON_PID_FMI: dict[tuple[int, int], str] = {
    (191, 7): "Mechanical system not responding (shift not completed)",
}

# Engine controller MIDs (SAE J1587 assigns these to engine ECUs).
ENGINE_MIDS = frozenset({128, 175, 183, 184, 185, 186})


def eaton_transmission_fault(is_sid: bool, number: int, fmi: int,
                             mid: int) -> Optional[str]:
    """Description for this record if it looks like a Fuller Top-2 fault.

    Returns ``None`` for anything not in the closed set, or for a non-engine
    MID (a real transmission controller names its own faults).
    """
    if mid not in ENGINE_MIDS:
        return None
    table = EATON_SID_FMI if is_sid else EATON_PID_FMI
    text = table.get((number, fmi))
    return f"{_PREFIX}{text}" if text else None
