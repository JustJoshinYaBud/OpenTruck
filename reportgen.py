"""OpenTruck - PDF diagnostic report generator.

Produces a clean, printable report in the spirit of a professional service-tool
printout. ``app._generate_report`` assembles the data into plain structures and
this module only does layout (no J1939/J1587 knowledge lives here).

Sections, in order
------------------
1. Header                 - tool name, "Diagnostic Report", generation timestamp.
2. Vehicle Identification - VIN, make, model, year (whichever are known).
3. Components             - discovered ECUs: system, description, serial/part,
                            software ID. Module names are tagged with their bus,
                            e.g. "Engine (J1939)" vs "Engine #1 (J1708)".
4. Engine Totals & Status - a curated set of J1939/J1587 counters (engine hours,
                            PTO hours, fuel used, engine speed, coolant, oil
                            pressure, battery voltage, road speed, ...) plus lamp
                            states (MIL / red / amber / protect). Values arrive
                            already converted to the user's unit system.
5. Fault Codes            - Active and Inactive tables: Module, Description,
                            SPN/PID, FMI, Count. Descriptions follow SAE J1939
                            (SPN/FMI) and SAE J1587 (PID/SID/FMI); the Module
                            column includes the bus tag.

Inputs
------
``generate_report(output_path, vin, make, model, year, components, totals,
lamps, active_dtcs, inactive_dtcs) -> bool``. See the function docstring for the
 exact dict shapes; every section is optional and omitted when empty.

Filename
--------
This module writes to whatever path it is given. The GUI builds the default name
as ``<ident>_<YYYY-MM-DD_HH-MM-SS>.pdf`` where ``<ident>`` is the engine serial,
else make/model, else VIN, else "OpenTruck" (see ``app._generate_report``).

Requires ``reportlab`` (see requirements.txt).

Not implemented yet (possible future additions): DPF soot-load % in the totals,
regen-cycle history, a full live-data appendix, CSV export, and multi-language
labels.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)

# Palette / styling.
ACCENT = colors.HexColor("#1F4E79")       # dark blue
ACCENT_LIGHT = colors.HexColor("#2E6DA4")
ROW_ALT = colors.HexColor("#F2F5F8")
GRID = colors.HexColor("#C7CFD8")
BODY = colors.HexColor("#222222")
MUTED = colors.HexColor("#666666")
GOOD = colors.HexColor("#1E7B34")
BAD = colors.HexColor("#B3261E")


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "brand": ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=22,
                                textColor=ACCENT, leading=26, spaceAfter=4),
        "doctitle": ParagraphStyle("doctitle", fontName="Helvetica-Bold",
                                   fontSize=13, textColor=BODY, spaceAfter=2),
        "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=9,
                               textColor=MUTED, spaceBefore=2, spaceAfter=10),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=12,
                                  textColor=ACCENT, spaceBefore=14, spaceAfter=2),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9,
                               textColor=BODY, leading=12),
        "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=9,
                                textColor=BODY, leading=12),
        "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=9,
                               textColor=MUTED, leading=12),
    }


def _header_table_style() -> TableStyle:
    """Shared style for section tables: accent header, striped rows, grid."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])


def _section(styles, title: str) -> list:
    return [
        Paragraph(title, styles["section"]),
        HRFlowable(width="100%", thickness=0.75, color=ACCENT_LIGHT,
                   spaceBefore=1, spaceAfter=8),
    ]


def generate_report(
    output_path: str,
    vin: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[int] = None,
    components=None,
    totals=None,
    lamps=None,
    active_dtcs=None,
    inactive_dtcs=None,
) -> bool:
    """Write the diagnostic report PDF. Returns True on success.

    components  : list[dict]  {name, description, serial, software}
    totals      : list[(label, value)]
    lamps       : list[(label, state)]
    active_dtcs : list[dict]  {module, description, spn, fmi, count}
    inactive_dtcs: list[dict] (same shape as active_dtcs)
    """
    components = components or []
    totals = totals or []
    lamps = lamps or []
    active_dtcs = active_dtcs or []
    inactive_dtcs = inactive_dtcs or []

    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=48, bottomMargin=54,
            title="OpenTruck Diagnostic Report",
        )
        s = _styles()
        el = []

        # ------------------------------------------------------------ header #
        now = datetime.now()
        el.append(Paragraph("OpenTruck", s["brand"]))
        el.append(Paragraph("Diagnostic Report", s["doctitle"]))
        el.append(Paragraph(
            f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
            s["meta"],
        ))

        # ----------------------------------------------- vehicle identification #
        el += _section(s, "Vehicle Identification")
        ident_rows = []
        if vin:
            ident_rows.append(["VIN", vin])
        if make:
            ident_rows.append(["Make", make])
        if model:
            ident_rows.append(["Model", model])
        if year:
            ident_rows.append(["Year", str(year)])
        if not ident_rows:
            ident_rows.append(["Identification", "No identification available"])
        id_table = Table(
            [[Paragraph(k, s["cellb"]), Paragraph(v, s["cell"])] for k, v in ident_rows],
            colWidths=[1.4 * inch, 5.4 * inch],
        )
        id_table.setStyle(_header_table_style())
        el.append(id_table)

        # ------------------------------------------------------- components #
        if components:
            el += _section(s, "Components")
            head = ["System", "Description", "Serial / Part", "Software ID"]
            rows = []
            for c in components:
                rows.append([
                    Paragraph(c.get("name", ""), s["cellb"]),
                    Paragraph(c.get("description", "") or "\u2014", s["cell"]),
                    Paragraph(c.get("serial", "") or "\u2014", s["cell"]),
                    Paragraph(c.get("software", "") or "\u2014", s["cell"]),
                ])
            comp = Table([head] + rows,
                         colWidths=[1.5 * inch, 2.2 * inch, 1.6 * inch, 1.5 * inch],
                         repeatRows=1)
            comp.setStyle(_header_table_style())
            el.append(comp)

        # -------------------------------------------------- totals & lamps #
        status_pairs = list(totals) + list(lamps)
        if status_pairs:
            el += _section(s, "Engine Totals & Status")
            # Two-column key/value layout.
            cells = []
            for k, v in status_pairs:
                cells.append(Paragraph(k, s["cellb"]))
                cells.append(Paragraph(str(v), s["cell"]))
            half = len(cells) // 2 + (len(cells) % 2)
            left, right = cells[:half], cells[half:]
            # pad right column to match row count
            while len(right) < len(left):
                right.append(Paragraph("", s["cell"]))
            grid_rows = []
            for i in range(0, len(left), 2):
                a = left[i:i + 2]
                b = right[i:i + 2] if i < len(right) else [Paragraph("", s["cell"])] * 2
                grid_rows.append(a + b)
            kv = Table(grid_rows, colWidths=[1.6 * inch, 1.2 * inch, 1.6 * inch, 1.5 * inch])
            kv.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, GRID),
            ]))
            el.append(kv)

        # ----------------------------------------------------- fault codes #
        el += _section(s, "Fault Codes")
        fc_head = ["Module", "Address", "Description", "SPN / PID", "FMI", "Count"]
        fc_widths = [1.4 * inch, 0.9 * inch, 2.0 * inch, 0.8 * inch, 0.5 * inch, 0.5 * inch]

        el.append(Paragraph("Active", s["cellb"]))
        if active_dtcs:
            rows = []
            for d in active_dtcs:
                rows.append([
                    Paragraph(d.get("module", "") or "\u2014", s["cell"]),
                    Paragraph(d.get("address", "") or "\u2014", s["cell"]),
                    Paragraph(d.get("description", "") or "\u2014", s["cell"]),
                    Paragraph(str(d.get("spn", "")), s["cell"]),
                    Paragraph(str(d.get("fmi", "")), s["cell"]),
                    Paragraph(str(d.get("count", 0)), s["cell"]),
                ])
            at = Table([fc_head] + rows, colWidths=fc_widths, repeatRows=1)
            at.setStyle(_header_table_style())
            el.append(at)
        else:
            el.append(Paragraph("No active fault codes.", s["note"]))

        el.append(Spacer(1, 10))
        el.append(Paragraph("Inactive", s["cellb"]))
        if inactive_dtcs:
            rows = []
            for d in inactive_dtcs:
                rows.append([
                    Paragraph(d.get("module", "") or "\u2014", s["cell"]),
                    Paragraph(d.get("address", "") or "\u2014", s["cell"]),
                    Paragraph(d.get("description", "") or "\u2014", s["cell"]),
                    Paragraph(str(d.get("spn", "")), s["cell"]),
                    Paragraph(str(d.get("fmi", "")), s["cell"]),
                    Paragraph(str(d.get("count", 0)), s["cell"]),
                ])
            it = Table([fc_head] + rows, colWidths=fc_widths, repeatRows=1)
            it.setStyle(_header_table_style())
            el.append(it)
        else:
            el.append(Paragraph("No inactive fault codes.", s["note"]))

        # ----------------------------------------------------------- footer #
        el.append(Spacer(1, 18))
        el.append(HRFlowable(width="100%", thickness=0.5, color=GRID))
        el.append(Paragraph(
            "Report generated by OpenTruck. Fault descriptions follow SAE J1939 "
            "(SPN/FMI) and SAE J1587 (PID/SID/FMI); consult the vehicle service "
            "manual for diagnostics.",
            s["note"],
        ))

        doc.build(el)
        return True

    except Exception as e:  # noqa: BLE001
        print(f"Report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
