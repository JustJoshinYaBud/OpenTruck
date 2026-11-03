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

FALLBACK POLICY (applies to EVERY OEM, present and future - do not make this
per-maker):
  * powertrain and brake modules - ``engine``, ``transmission``,
    ``aftertreatment``, ``brakes``/``abs``/``ebs`` - keep the generic SAE name
    when the maker has no entry, because those SPNs really are the standard
    parameters on every brand;
  * every other module class - body / chassis / cab: body controller, cluster,
    HVAC, doors, steering, suspension, telematics, and anything we cannot
    classify - reports **"Refer to OEM"** instead of guessing, because makers
    routinely repurpose standard SPNs on those modules;
  * a code with the J1939 conversion-method bit set (CM=1) always reports
    "Refer to OEM" (annotated "(manufacturer-specific)" where a name is known).

A new OEM therefore needs NO extra flag to get this behaviour: adding a table
only ever *adds* correct names. See ``_TRUSTED_GENERIC_PREFIXES``.
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
from lookup.oem_navistar import NAVISTAR_SPN_FMI, NAVISTAR_ADDRESSES
from lookup.oem_detroit import DETROIT_SPN_FMI
from lookup.oem_volvo import (VOLVO_PID, VOLVO_SID, VOLVO_SPN,
                              VOLVO_ADDRESSES, MACK_ADDRESSES)
from lookup.oem_deutz import DEUTZ_SPN_FMI
from lookup.oem_paccar import PACCAR_ADDRESSES
from lookup.oem_kubota import KUBOTA_SPN_FMI
from lookup.oem_perkins import PERKINS_SPN_FMI, PERKINS_EVENTS
from lookup.oem_dtna import DTNA_ADDRESSES, DTNA_SPN_FMI, DTNA_SPN_FMI_BULKHEAD


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
    # Live-data wording: canonical decoded parameter name -> the maker's own
    # name for it. Display-only (the stored value, CSV key and graph key stay
    # canonical), so a maker's vocabulary never corrupts the decode itself.
    live: dict[str, str] = field(default_factory=dict)
    # J1939 source address -> the maker's own name for the module on that
    # address. Used only when the CHASSIS is known to be this maker, and only as
    # a fallback for a module that never claims an address (NAME/CI still win).
    addresses: dict[int, str] = field(default_factory=dict)



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
            live={
                # Caterpillar calls cooled EGR "Clean Gas Induction" (CGI).
                "EGR 1 Mass Flow": "Clean Gas Induction (CGI) 1 Mass Flow",
                "EGR 2 Mass Flow": "Clean Gas Induction (CGI) 2 Mass Flow",
            },
        ),
        OEM(
            id="cummins",
            label="Cummins",
            make_keys=("CUMMINS", "CMI", "CMMNS"),
            mfr_codes=(10, 440),
            spn_fmi=CUMMINS_SPN_FMI,
            sid_fmi=CUMMINS_SID_FMI,
            pid_fmi=CUMMINS_PID_FMI,
            live={
                # Cummins uses "Intake Charge Pressure" (ICP) instead of SAE's
                # "Fuel Delivery Pressure" for SPN 94. Also prefers shorter names.
                "Fuel Delivery Pressure": "Intake Charge Pressure (ICP)",
                "Air Filter Differential Pressure": "Air Restriction",
            },
        ),
        OEM(
            id="paccar",
            label="PACCAR",
            # Kenworth/Peterbilt arrive as their own CI make strings, so they
            # must select this entry too (the chassis map only applies when the
            # VIN WMI names one of them).
            make_keys=("PACCAR", "KENWORTH", "PETERBILT"),
            mfr_codes=(45,),
            addresses=PACCAR_ADDRESSES,
            live={
                # PACCAR uses "Compression Brake Torque" (Jake Brake terminology)
                # instead of SAE's "Actual Retarder Torque".
                # Also prefers "Air Restriction" over the verbose SAE name.
                "Actual Retarder Torque": "Compression Brake Torque",
                "Air Filter Differential Pressure": "Air Restriction",
            },
        ),
        OEM(
            id="detroit",
            label="Detroit Diesel",
            make_keys=("DETROIT", "DDC"),
            mfr_codes=(14,),
            spn_fmi=DETROIT_SPN_FMI,
            live={
                # Detroit Diesel uses "ICP" instead of SAE's "Fuel Delivery Pressure"
                # Also prefers "Air Restriction" over the verbose SAE name.
                "Fuel Delivery Pressure": "ICP",
                "Air Filter Differential Pressure": "Air Restriction",
            },
        ),
        OEM(
            id="mack",
            label="Mack Trucks",
            make_keys=("MACK",),
            mfr_codes=(37,),
            # Mack MP7/MP8/MP10 are Volvo-built engines sharing the Volvo ECM,
            # so the Volvo cross-reference applies to them as well.
            spn=VOLVO_SPN,
            pid=VOLVO_PID,
            sid=VOLVO_SID,
            addresses=MACK_ADDRESSES,
            live={
                # Volvo/Mack use "Retarder Torque" instead of SAE's verbose
                # "Actual Retarder Torque" terminology.
                "Actual Retarder Torque": "Retarder Torque",
            },
        ),
        OEM(
            id="volvo",
            label="Volvo",
            make_keys=("VOLVO",),
            mfr_codes=(60, 61),
            spn=VOLVO_SPN,
            pid=VOLVO_PID,
            sid=VOLVO_SID,
            addresses=VOLVO_ADDRESSES,
            live={
                # Volvo uses "Retarder Torque" instead of SAE's verbose
                # "Actual Retarder Torque" terminology.
                "Actual Retarder Torque": "Retarder Torque",
            },
        ),
        # NOTE: the Mercedes-Benz *engine* identity (MBE) and the DTNA *chassis*
        # identity are one entry on purpose - an OM906 in a Sterling and the
        # body controller on a Cascadia are the same corporate family, and
        # splitting them produced confusion (a Freightliner chassis matching the
        # Mercedes entry via the "DAIMLER" prefix). Everything Daimler lands
        # here; per-brand/per-model behaviour can be added later with model keys
        # rather than a second OEM entry.
        OEM(
            id="dtna",
            label="Daimler Truck / DTNA (Freightliner, Western Star, Sterling, "
                  "Mercedes-Benz engines)",
            make_keys=("FREIGHTLINER", "WESTERN STAR", "STERLING",
                       "DAIMLERCHRYSLER", "DAIMLER TRUCKS", "DTNA",
                       "MERCEDES", "MRCBN", "DAIMLER-BENZ"),
            mfr_codes=(25, 79),
            addresses=DTNA_ADDRESSES,
            spn_fmi=DTNA_SPN_FMI,
            sid_fmi=DTNA_SPN_FMI_BULKHEAD,
        ),
        OEM(
            id="kubota",
            label="Kubota",
            make_keys=("KUBOTA",),
            mfr_codes=(416,),
            spn_fmi=KUBOTA_SPN_FMI,
        ),
        OEM(
            id="perkins",
            label="Perkins",
            make_keys=("PERKINS",),
            mfr_codes=(93,),
            spn_fmi=PERKINS_SPN_FMI,
            events=PERKINS_EVENTS,
        ),
        OEM(
            id="deutz",
            label="Deutz",
            # "DEUTZ AG" arrives as the CI make string; 352 is SAME Deutz-Fahr,
            # the only Deutz-group code in the SAE manufacturer registry.
            make_keys=("DEUTZ",),
            mfr_codes=(352,),
            spn_fmi=DEUTZ_SPN_FMI,
        ),
        OEM(
            id="navistar",
            label="Navistar / International",
            make_keys=("INTERNATIONAL", "NAVISTAR", "INT"),
            mfr_codes=(42, 43),
            spn_fmi=NAVISTAR_SPN_FMI,
            addresses=NAVISTAR_ADDRESSES,
            live={
                # The Navistar / MaxxForce ECM reports battery potential in
                # VEP1 bytes 6-7; bytes 4-5 are left empty, so the standard
                # "Battery Voltage" parameter is never produced and the value
                # arrives as the charging-system field. Present it correctly.
                "Charging System Voltage": "Battery Voltage",
            },
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

    **Module class decides the fallback** (applies to every maker equally):
    powertrain and brake controllers keep the generic SAE name, because those
    SPNs really are the standard parameters. Chassis / body / cab modules show
    "Refer to OEM" instead, because OEMs routinely repurpose standard SPNs
    there - e.g. a DTNA body controller flagging a *TPMS setting* SPN with a
    network-data FMI. A code with CM=1 always reads "Refer to OEM" as well.
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
    if specific is None and not _generic_name_trusted(component):
        # A module whose codes we cannot vouch for: the generic SAE name is more
        # likely wrong than right, so say "Refer to OEM" instead of naming a
        # parameter the module may not even use. Applies to EVERY maker - see
        # _generic_name_trusted for which module classes keep the generic name.
        return UNRESOLVED_CODE
    base = specific if specific is not None else (spn_name(spn) or UNRESOLVED_CODE)
    if cm:
        return f"{base} (manufacturer-specific)"
    return base


# Module roles whose SPNs really are the standard SAE parameters, so a generic
# name is safe even when the maker has no table for that particular code. These
# are the classes where the SAE registry is authoritative in practice: an engine
# ECM's SPN 110 is coolant temperature on every brand.
_TRUSTED_GENERIC_PREFIXES = (
    "engine",              # includes "Engine #1", "Engine ECM"
    "transmission",        # includes "Transmission #1", TCM, gear-shift ECU
    "aftertreatment",      # ACM / SCR / DPF controllers
    "exhaust aftertreatment",
    "brakes",              # ABS / EBS / axle brake controllers
    "abs",
    "ebs",
)


def _generic_name_trusted(component: str | None) -> bool:
    """Whether a generic SAE name may be shown for this module role.

    Chassis / body / cab modules (body controller, cluster, HVAC, door pods,
    steering, suspension, telematics...) are the classes where OEMs routinely
    repurpose standard SPNs - and where the generic name is therefore a guess.
    Those show "Refer to OEM" unless the maker has an entry for the code.
    Unknown roles (None) are treated as untrusted: better to say "look it up"
    than to name a parameter the vehicle may not use at all.
    """
    c = (component or "").strip().lower()
    if not c:
        return False
    return c.startswith(_TRUSTED_GENERIC_PREFIXES)


def address_label(addr: int, make: str | None = None,
                  mfr: int | None = None) -> str | None:
    """The maker's own name for a source address, or None.

    OEMs reuse the standard preferred addresses, so a maker's own SA map beats
    the generic J1939-71 table when we know whose chassis this is.
    """
    for oem in select_oems(make, mfr):
        label = oem.addresses.get(addr)
        if label:
            return label
    return None


def resolve_live_label(name: str, make: str | None = None,
                       mfr: int | None = None) -> str:
    """The maker's wording for a decoded live parameter, else ``name``.

    Display-only: callers keep the canonical name as the data key (graph,
    CSV params, report lookups), so a maker's vocabulary can never break the
    decode or a stored log.
    """
    for oem in select_oems(make, mfr):
        label = oem.live.get(name)
        if label:
            return label
    return name


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
