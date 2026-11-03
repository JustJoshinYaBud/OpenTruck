"""OpenTruck - Deutz engine / equipment fault-code table.

SPN+FMI -> short component name, taken from **DEUTZ's own published DTC lists**
(`serdia.deutz.com`, "DEUTZ DTC-Codes EMR5" / "DTC-Codes for Bosch MD1 ECUs").
These are the engine maker's own documents, so the source is legitimate; only
the short factual component name is stored here. The failure-mode wording stays
generic (SAE J1939-73) and is added at display time, so a code still reads
sensibly and no authored prose is redistributed.

Notes
-----
* Deutz also publishes a DTC-Code (Pxxxx) per row; that number is what their
  service tool shows. We key on SPN+FMI because that is what the bus carries.
* Only the rows visible in the public lists are included - this is not the
  complete Deutz dictionary, and some engine series (EMR2/EMR3) have their own
  lists that are not merged here yet.
* Scoped to Deutz only (make string "DEUTZ", plus the SAME Deutz-Fahr
  manufacturer code 352), so it can never leak into another maker.
"""

# (SPN, FMI) -> short component / condition name
DEUTZ_SPN_FMI: dict[tuple[int, int], str] = {
    # --- engine sensors / actuators ---------------------------------------
    (27, 4): "EGR actuator position",
    (51, 3): "Throttle valve / throttle valve position",
    (51, 4): "Throttle valve / throttle valve position",
    (91, 4): "Accelerator pedal position 1",
    (91, 11): "Accelerator pedal position 1",
    (97, 4): "Water-in-fuel sensor",
    (100, 4): "Oil pressure sensor",
    (107, 4): "Air filter differential pressure sensor",
    (108, 4): "Ambient pressure sensor",
    (157, 3): "Fuel rail pressure sensor",
    (175, 0): "Oil temperature",
    (629, 12): "Engine ECU (internal failure)",
    (677, 3): "Starter relay",
    (677, 4): "Starter relay",
    (677, 5): "Starter relay",
    (7103, 3): "Fuel metering unit",
    (7103, 4): "Fuel metering unit",
    (2625, 3): "Accelerator pedal 2 (sensor 2)",
    # --- exhaust / aftertreatment -----------------------------------------
    (97, 3): "Water-in-fuel sensor",
    (3532, 3): "DEF tank level sensor",
    (4376, 3): "DEF reverse valve",
    (4376, 4): "DEF reverse valve",
    (5491, 3): "DEF suction line",
    (5746, 4): "DEF metering unit heater relay",
    (7459, 3): "DEF pump pressure (SM8 pump)",
    (520294, 14): "Particle diagnostic - power reduction step 1",
    (520315, 11): "Exhaust throttle valve (ETV) actuator - light fault",
    (520436, 3): "DEF quality sensor",
    (520436, 4): "DEF quality sensor",
    (520496, 11): "Exhaust flap - internal fault",
    (520497, 11): "Exhaust flap - external fault",
    (520498, 13): "Exhaust flap - learning fault",
    (524065, 3): "Pressure sensor before SCR catalyst",
    # --- ECU / network ----------------------------------------------------
    (520323, 11): "CAN main secondary - fault trigger on secondary ECU",
    (520332, 11): "Collective fault - software reset failure (secondary)",
    (520333, 11): "Collective fault - no engine speed signal (secondary)",
    (520334, 11): "Collective fault - ETV light fault (secondary)",
    (520337, 11): "Collective fault - NOx sensor downstream failure (secondary)",
    (520338, 11): "Collective fault - ETV safety position (secondary)",
    (520341, 11): "Collective fault - DEF pressure problem (secondary)",
    (520344, 11): "Collective fault - SCR system failure (secondary)",
    (520349, 11): "Collective fault - SCR system failure (secondary)",
    (520353, 11): "Collective fault - DOC/DPF system failure (secondary)",
    (520355, 11): "Collective fault - sensor supply voltage failure (secondary)",
    (520364, 11): "Collective fault - ECU EEPROM failure (secondary)",
    (520365, 11): "Collective fault - battery voltage failure (secondary)",
    (520366, 11): "Collective fault - CAN failure (secondary)",
    (520368, 11): "Collective fault - ECU hardware failure (secondary)",
    (520369, 11): "Collective fault - ECU temperature failure (secondary)",
    (520461, 11): "Collective fault - ambient pressure sensor failure (secondary)",
    (520462, 11): "Collective fault - SCR system failure (secondary)",
    (520463, 11): "Collective fault - NH3 sensor failure (secondary)",
    (520466, 11): "Power reduction 50% triggered by secondary ECU fault",
    (520470, 11): "Standstill regeneration request from secondary ECU",
    (520473, 31): "Wrong engine ECU",
    (520477, 11): "CAN main secondary - fault trigger on secondary ECU",
    (520484, 11): "Collective fault - DEF pump motor failure (secondary)",
    (520485, 11): "Collective fault - SCR system failure (secondary)",
    (520486, 11): "Collective fault - SCR system failure (secondary)",
    (520487, 13): "Inconsistent data set on main and secondary ECU",
    (520500, 14): "Engine ECU - internal diagnostic error",
    (520414, 2): "CAN main secondary - time synchronisation fault",
    (523982, 1): "Power stage diagnostic",
    (520458, 3): "Engine running lamp",
    (520458, 4): "Engine running lamp",
}

# Deutz "replacement fault code triggered by FID ..." rows (condition exists).
# Kept generic on purpose - the FID reference is the useful part.
DEUTZ_REPLACEMENT_FIDS: dict[int, str] = {
    520441: "UVMDSM13",
    521000: "ExtdInhbn01",
    521001: "ExtdInhbn02",
    521002: "ExtdInhbn03",
    521003: "ExtdInhbn04",
    521004: "ExtdInhbn05",
    521005: "ExtdInhbn06",
    521009: "ExtdInhbn07",
    521010: "ExtdInhbn08",
    521011: "ExtdInhbn09",
    521018: "ExtdInhbn010",
    521012: "ExtdInhbn11",
}

for _spn, _fid in DEUTZ_REPLACEMENT_FIDS.items():
    DEUTZ_SPN_FMI.setdefault(
        (_spn, 31), f"Replacement fault code triggered by FID {_fid}")
