"""OpenTruck - OEM registry and shared selector for brand-specific lookups.

Generic J1939/J1587 decoding uses the pure SAE tables in ``spn.py`` and
``pid1587.py`` and must never be contaminated with one maker's private
numbering. But several OEMs repurpose their own code numbers (or add entirely
new ones) that the generic tables can't name. This module holds those in a
single, clean place:

  * ``OEM`` / ``REGISTRY`` - one entry per manufacturer. Each entry carries the
    identities that select it (make tokens, J1939 NAME manufacturer codes) plus
    its override tables for each code family:
        ``spn``  - J1939 SPN -> maker-specific description (repurposed SPNs)
        ``pid``  - J1587 "PID" slot -> maker-specific name (e.g. a CAT "CID")
        ``sid``  - J1587 SID -> maker-specific name
        ``events`` - maker event-code -> description (reference only)

  * ``select_oems`` - the shared selector: turns a module's identity (make
    string and/or NAME manufacturer code) into the OEM entries that apply.

  * resolution helpers / ``resolve_code_description`` - the lookup path that
    tries the selected OEM's override first, then the generic SAE table, so a
    maker-specific meaning is used **only** for that maker and can never leak
    into a different vehicle.

Adding a new OEM is a single ``OEM(...)`` literal appended to ``REGISTRY`` - no
decode logic or generic-table changes are required.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lookup.spn import spn_name, UNRESOLVED_CODE
from lookup.oem_cat import CAT_PID, CAT_EVENTS, CAT_SPN
from lookup.oem_jd import JD_SPN_FMI
from lookup.oem_wabco import WABCO_SPN_FMI, WABCO_SID_FMI
from lookup.oem_cummins import CUMMINS_SPN_FMI, CUMMINS_SID_FMI, CUMMINS_PID_FMI
from lookup.oem_bendix import BENDIX_SID
from lookup.oem_haldex import HALDEX_SID_FMI
from lookup.oem_navistar import NAVISTAR_SPN_FMI
from lookup.oem_detroit import DETROIT_SPN_FMI
from lookup.oem_volvo import VOLVO_PID, VOLVO_SID


@dataclass(frozen=True)
class OEM:
    id: str                       # canonical key, e.g. "caterpillar"
    label: str                    # display name, e.g. "Caterpillar"
    make_keys: tuple[str, ...] = ()       # uppercase make prefixes ("CAT", ...)
    mfr_codes: tuple[int, ...] = ()       # J1939 NAME manufacturer codes (8 = CAT)
    spn: dict[int, str] = field(default_factory=dict)   # SPN -> OEM description
    spn_fmi: dict[tuple[int, int], str] = field(default_factory=dict)  # (SPN,FMI) -> text
    sid_fmi: dict[tuple[int, int], str] = field(default_factory=dict)  # (SID,FMI) -> text
    pid_fmi: dict[tuple[int, int], str] = field(default_factory=dict)  # (PID,FMI) -> text
    pid: dict[int, str] = field(default_factory=dict)   # J1587 PID slot -> name
    sid: dict[int, str] = field(default_factory=dict)   # J1587 SID -> name
    events: dict[str, str] = field(default_factory=dict)  # event code -> name


# --- Registry --------------------------------------------------------------- #
# One entry per OEM. ``pid`` doubles as the maker's CDL component identifiers
# (CAT reports its "CID" number in the J1587 PID slot rather than a standard SAE
# PID). ``spn`` is reserved for maker-proprietary J1939 SPNs.
#
# The identities (``make_keys`` / ``mfr_codes``) are standard SAE facts and are
# populated for all major engine/truck OEMs below. The *proprietary* override
# tables (``spn`` / ``pid`` / ``sid`` / ``events``) are only filled in once a
# trustworthy source is available - Caterpillar is populated from the official
# REHS0126-33 document (``lookup/oem_cat.py``); the rest are still empty.
REGISTRY: dict[str, OEM] = {
    oem.id: oem
    for oem in (
        OEM(
            id="caterpillar",
            label="Caterpillar",
            make_keys=("CAT",),
            mfr_codes=(8,),
            spn=CAT_SPN,
            pid=CAT_PID,
            events=CAT_EVENTS,
        ),
        OEM(
            id="cummins",
            label="Cummins",
            make_keys=("CUMMINS", "CMI", "CMMNS"),
            mfr_codes=(10, 440),
            spn_fmi=CUMMINS_SPN_FMI,
            sid_fmi=CUMMINS_SID_FMI,
            pid_fmi=CUMMINS_PID_FMI,
        ),
        OEM(
            id="paccar",
            label="PACCAR",
            make_keys=("PACCAR",),
            mfr_codes=(45,),
        ),
        OEM(
            id="detroit",
            label="Detroit Diesel",
            make_keys=("DETROIT", "DDC"),
            mfr_codes=(14,),
            spn_fmi=DETROIT_SPN_FMI,
        ),
        OEM(
            id="mack",
            label="Mack Trucks",
            make_keys=("MACK",),
            mfr_codes=(37,),
            # Mack MP7/MP8/MP10 are Volvo-built engines sharing the Volvo ECM,
            # so the Volvo cross-reference applies to them as well.
            pid=VOLVO_PID,
            sid=VOLVO_SID,
        ),
        OEM(
            id="volvo",
            label="Volvo",
            make_keys=("VOLVO",),
            mfr_codes=(60, 61),
            pid=VOLVO_PID,
            sid=VOLVO_SID,
        ),
        OEM(
            id="mercedes",
            label="Mercedes-Benz",
            make_keys=("MERCEDES", "DAIMLER", "MRCBN"),
            mfr_codes=(79,),
        ),
        OEM(
            id="navistar",
            label="Navistar / International",
            make_keys=("INTERNATIONAL", "NAVISTAR", "INT"),
            mfr_codes=(42, 43),
            spn_fmi=NAVISTAR_SPN_FMI,
        ),
        OEM(
            id="johndeere",
            label="John Deere",
            make_keys=("JOHN DEERE", "DEERE"),
            mfr_codes=(33, 66, 67, 75, 77),
            spn_fmi=JD_SPN_FMI,
        ),
        OEM(
            id="wabco",
            label="WABCO",
            make_keys=("WABCO", "ZF"),
            mfr_codes=(62, 63),
            spn_fmi=WABCO_SPN_FMI,
            sid_fmi=WABCO_SID_FMI,
        ),
        OEM(
            id="bendix",
            label="Bendix",
            make_keys=("BENDIX", "BNDWS"),
            mfr_codes=(1, 83),
            sid=BENDIX_SID,
        ),
        OEM(
            id="haldex",
            label="Haldex",
            make_keys=("HALDEX",),
            sid_fmi=HALDEX_SID_FMI,
        ),
        # --- truck OEMs with identities only (no proprietary code tables yet) --
        # An entry with empty override tables is harmless: select_oems() returns
        # it, every resolve_*() lookup misses, and decoding falls back to the
        # pure SAE tables. They exist so the maker is NAMED correctly and so a
        # future table only needs adding here.
        OEM(
            id="daimler",
            label="Daimler Truck (Freightliner / Western Star / Sterling)",
            make_keys=("FREIGHTLINER", "WESTERN STAR", "STERLING", "DAIMLER"),
            mfr_codes=(25,),
        ),
        # --- heavy / construction equipment (identities only) ------------------
        OEM(
            id="komatsu",
            label="Komatsu",
            make_keys=("KOMATSU",),
            mfr_codes=(136,),
        ),
        OEM(
            id="hitachi",
            label="Hitachi Construction Machinery",
            make_keys=("HITACHI",),
            mfr_codes=(725, 886),
        ),
        OEM(
            id="cnh",
            label="CNH Industrial (Case / New Holland)",
            make_keys=("CASE", "NEW HOLLAND", "CNH"),
            mfr_codes=(7, 94, 213),
        ),
        OEM(
            id="bobcat",
            label="Bobcat (Doosan/Ingersoll-Rand)",
            make_keys=("BOBCAT", "DOOSAN", "INGERSOLL"),
            mfr_codes=(82, 556, 1266),
        ),
        OEM(
            id="jcb",
            label="JCB",
            make_keys=("JCB",),
            mfr_codes=(87,),
        ),
        OEM(
            id="liebherr",
            label="Liebherr",
            make_keys=("LIEBHERR",),
            mfr_codes=(729,),
        ),
        OEM(
            id="volvoce",
            label="Volvo Construction Equipment",
            make_keys=("VOLVO CE",),
            mfr_codes=(1061,),
        ),
    )
}


# --- Shared selector -------------------------------------------------------- #
def select_oems(make: str | None = None, mfr: int | None = None) -> list[OEM]:
    """Select the OEM entries that a module's identity matches.

    ``make`` is a (possibly free-form) make string; ``mfr`` is a J1939 NAME
    manufacturer code. Either may be unknown; both are matched against each
    registered OEM. Returns an empty list when no OEM matches (the caller then
    falls back to the generic SAE tables).
    """
    mk = (make or "").strip().upper()
    out: list[OEM] = []
    for oem in REGISTRY.values():
        if mk and any(mk.startswith(k) for k in oem.make_keys):
            out.append(oem)
            continue
        if mfr is not None and mfr in oem.mfr_codes:
            out.append(oem)
    return out


# --- Resolution (generic / component / OEM overrides) ----------------------- #
# Component (function) specific SPN overrides, independent of brand - e.g. a
# "Brakes - Steering Axle" controller may repurpose an SPN regardless of vendor.
COMPONENT_SPN_OVERRIDES: dict[str, dict[int, str]] = {}


def resolve_code_description(
    spn: int,
    fmi: int,
    component: str | None = None,
    make: str | None = None,
    mfr: int | None = None,
    cm: int = 0,
) -> str:
    """Best description for a J1939 code, using vehicle/component identity.

    Resolution order: (1) an OEM-specific SPN+FMI override (from the selected
    OEM), (2) an OEM-specific SPN override, (3) a component/function override,
    (4) the generic SAE name. A code with CM=1 uses a manufacturer's own
    conversion method, so the result is annotated "(manufacturer-specific)"
    rather than silently shown under the generic name.
    """
    oems = select_oems(make=make, mfr=mfr)
    specific = None
    for oem in oems:
        specific = oem.spn_fmi.get((spn, fmi))
        if specific is not None:
            break
    if specific is None:
        for oem in oems:
            specific = oem.spn.get(spn)
            if specific is not None:
                break
    if specific is None and component:
        specific = COMPONENT_SPN_OVERRIDES.get(component, {}).get(spn)
    base = specific if specific is not None else (spn_name(spn) or UNRESOLVED_CODE)
    if cm:
        return f"{base} (manufacturer-specific)"
    return base


def resolve_pid_name(pid: int, fmi: int | None = None,
                     make: str | None = None,
                     mfr: int | None = None) -> str | None:
    """OEM-specific name for a J1587 "PID" slot number, or None.

    When ``fmi`` is given, an OEM's (PID, FMI) override is tried first (Cummins
    describes each fault per PID+FMI), then the bare PID override (e.g. a CAT CID).
    """
    oems = select_oems(make=make, mfr=mfr)
    if fmi is not None:
        for oem in oems:
            name = oem.pid_fmi.get((pid, fmi))
            if name is not None:
                return name
    for oem in oems:
        name = oem.pid.get(pid)
        if name is not None:
            return name
    return None


def resolve_sid_name(sid: int, fmi: int | None = None,
                     make: str | None = None,
                     mfr: int | None = None) -> str | None:
    """OEM-specific name for a J1587 SID number, or None.

    When ``fmi`` is given, an OEM's (SID, FMI) override is tried first (WABCO
    describes each fault per SID+FMI combination), then the bare SID override.
    """
    oems = select_oems(make=make, mfr=mfr)
    if fmi is not None:
        for oem in oems:
            name = oem.sid_fmi.get((sid, fmi))
            if name is not None:
                return name
    for oem in oems:
        name = oem.sid.get(sid)
        if name is not None:
            return name
    return None
