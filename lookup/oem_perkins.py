"""OpenTruck - Perkins engine fault-code / event-code table.

Built from the OFFICIAL Perkins publication **TPD1836** ("Electrical &
Electronic Application and Installation Manual", 1200F series) - the tables that
pair a service-tool description, a J1939 SPN/FMI and a Perkins *event code*
(e.g. ``110-15`` = ``E361-1``).

Only the monitored items Perkins documents in that manual are covered; it is an
application/installation manual, not a complete fault dictionary, so this table
is deliberately small. Event codes are kept alongside the SPN/FMI pair because
Perkins service literature and their EST tool quote them.

Short factual descriptions only; the FMI failure phrase is added generically at
display time.

Scoped to Perkins (manufacturer code 93).
"""

# (SPN, FMI) -> short description
PERKINS_SPN_FMI: dict[tuple[int, int], str] = {
    (97, 15): "Water in fuel switch",
    (110, 15): "Engine coolant temperature - high (least severe)",
    (110, 16): "Engine coolant temperature - high (moderate severity)",
    (110, 0): "Engine coolant temperature - high (most severe)",
    (111, 17): "Engine coolant level - low",
    (190, 15): "Engine overspeed",
    (412, 15): "High exhaust (NRS) temperature - least severe",
    (412, 16): "High exhaust (NRS) temperature - moderate severity",
    (441, 17): "Auxiliary temperature #1 - low",
    (1387, 15): "Auxiliary pressure #1 - low",
    (1761, 17): "DEF tank level - low (least severe)",
    (1761, 18): "DEF tank level - low (moderate severity)",
    (1761, 1): "DEF tank level - low (most severe)",
    (5246, 15): "SCR operator inducement - level 1",
    (5246, 16): "SCR operator inducement - level 2",
    (5246, 0): "SCR operator inducement - level 3",
    (5435, 7): "DEF dosing system - loss of prime",
    (434, 18): "DEF dosing reagent pressure - low",
}

# Perkins event code -> (SPN, FMI), for readers who have the event code instead.
PERKINS_EVENTS: dict[str, tuple[int, int]] = {
    "E232-1": (97, 15),
    "E361-1": (110, 15),
    "E361-2": (110, 16),
    "E361-3": (110, 0),
    "E362-1": (190, 15),
    "E1092-1": (412, 15),
    "E1092-3": (412, 16),
    "E2143-1": (111, 17),
    "E445-1": (441, 17),
    "E443-1": (1387, 15),
}
