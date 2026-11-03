"""OpenTruck - synthetic J1939 frame source (no hardware required).

Emits a looping script of Address-Claimed + DM1/DM2 frames for a handful of
fake ECUs, so the GUI and the Session logic can be developed/tested on any
machine with no vehicle or adapter attached.
"""
from __future__ import annotations

import time
from typing import Optional

from framesource import FrameSource
from modules.j1939 import Frame, PGN


def _name(function: int, manufacturer: int, identity: int) -> bytes:
    """Build an 8-byte J1939 NAME from the fields we care about."""
    n = (
        (identity & 0x1FFFFF)
        | ((manufacturer & 0x7FF) << 21)
        | ((function & 0xFF) << 40)
    )
    return n.to_bytes(8, "little")


def _dtc(spn: int, fmi: int) -> bytes:
    """Encode a single 4-byte DTC (SPN 19-bit + FMI 5-bit + CM + OC)."""
    b0 = spn & 0xFF
    b1 = (spn >> 8) & 0xFF
    b2 = (((spn >> 16) & 0x07) << 5) | (fmi & 0x1F)
    b3 = 0  # conversion method 0, occurrence count 0
    return bytes([b0, b1, b2, b3])


class SimulatorSource(FrameSource):
    def __init__(self, fps: float = 25.0) -> None:
        self._period = 1.0 / fps
        self._i = -1
        self._frames = self._build_script()

    @staticmethod
    def _build_script() -> list[Frame]:
        f: list[Frame] = []
        # Address claims (Engine SA 0, Transmission SA 3, Brakes/ABS SA 11)
        f += [Frame(PGN.ADDRESS_CLAIMED, _name(0, 440, 1000), source=0)]
        f += [Frame(PGN.ADDRESS_CLAIMED, _name(3, 7, 2000), source=3)]
        f += [Frame(PGN.ADDRESS_CLAIMED, _name(11, 99, 3000), source=11)]
        # Engine DM1: MIL+red lamps, two DTCs (coolant temp above normal,
        # oil temp below normal / open circuit)
        f += [Frame(PGN.DM1, bytes([0x50, 0xFF]) + _dtc(110, 0) + _dtc(175, 5), source=0)]
        # Transmission DM1: no lamps, no DTCs
        f += [Frame(PGN.DM1, bytes([0x00, 0xFF]), source=3)]
        # ABS DM1: amber lamp, wheel-speed abnormal update rate
        f += [Frame(PGN.DM1, bytes([0x04, 0xFF]) + _dtc(84, 9), source=11)]
        # Engine DM2 (previously active): coolant level low
        f += [Frame(PGN.DM2, bytes([0x00, 0xFF]) + _dtc(111, 1), source=0)]
        # Vehicle identification (Component ID + VIN) for the engine
        f += [Frame(PGN.CI, b"Cummins*ISX15*7923456*1*", source=0)]
        f += [Frame(PGN.VI, b"1XKYDP9X7FJ469058*", source=0)]
        # Live-data broadcasts (decoded by livedata.decode_live) so the
        # "Live Data" panel has something to show without real hardware.
        f += [
            Frame(PGN.EEC1, bytes([0x00, 125, 140, 0x80, 0x25, 0x00, 0x00, 0x00]), source=0),
            Frame(0xF003, bytes([0x00, 60, 0x00, 45, 0x00]), source=0),          # EEC2
            Frame(PGN.ECT1, bytes([118, 96, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00]), source=0),
            Frame(PGN.VDH, bytes([0xF0, 0x00, 0x58, 0x7D, 0x00, 0x00, 0x00, 0xFF]), source=0),  # CCVS1 road speed
            Frame(PGN.AMB, bytes([0xC8, 0x00]), source=0),
            Frame(0xF005, bytes([0x00, 0x00, 0x00, 0x00, 0x40, 0x0E, 0x00, 0x00]), source=3),  # ETC1
        ]
        return f

    def connect(self) -> None:
        self._i = -1

    def read_frame(self) -> Optional[Frame]:
        time.sleep(self._period)
        self._i = (self._i + 1) % len(self._frames)
        return self._frames[self._i]

    def write_frame(self, frame: Frame) -> None:
        pass  # simulator ignores transmits

    def close(self) -> None:
        pass
