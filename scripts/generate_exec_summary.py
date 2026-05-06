"""Generate the Nexus Agent executive summary as a .docx file.

Run:  python scripts/generate_exec_summary.py
Output: reports/nexus_agent_executive_summary.docx
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "nexus_agent_executive_summary.docx"


# ---- helpers --------------------------------------------------------------

def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_cell_borders(cell, color: str = "BFBFBF", size: int = 6) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:color"), color)
        borders.append(b)
    tc_pr.append(borders)


def _add_horizontal_rule(paragraph, color: str = "2E75B6") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _style_default_font(doc: Document) -> None:
    # Set Arial 11pt as the document default.
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)


def _restyle_heading(doc: Document, level: int, *, size: int, color: str = "1F3864") -> None:
    style = doc.styles[f"Heading {level}"]
    style.font.name = "Arial"
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = RGBColor.from_string(color)


def _set_letter_page(doc: Document) -> None:
    section = doc.sections[0]
    section.page_height = Inches(11)
    section.page_width = Inches(8.5)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)


def _add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        p.paragraph_format.space_after = Pt(2)


def _add_table(doc: Document, headers: list[str], rows: list[list[str]],
               col_widths_inches: list[float] | None = None) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.autofit = False

    # Header row.
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor.from_string("FFFFFF")
        run.font.size = Pt(10)
        _set_cell_shading(cell, "1F3864")
        _set_cell_borders(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Body rows.
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            cell = table.rows[r].cells[c]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            run.font.size = Pt(10)
            _set_cell_borders(cell)
            if r % 2 == 0:
                _set_cell_shading(cell, "F2F2F2")

    # Column widths.
    if col_widths_inches:
        for col_idx, w in enumerate(col_widths_inches):
            for row in table.rows:
                row.cells[col_idx].width = Inches(w)


# ---- content --------------------------------------------------------------

def build() -> None:
    doc = Document()
    _set_letter_page(doc)
    _style_default_font(doc)
    _restyle_heading(doc, 1, size=18)
    _restyle_heading(doc, 2, size=14)
    _restyle_heading(doc, 3, size=12, color="2E75B6")

    # ---- Title block --------------------------------------------------
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Nexus Agent")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor.from_string("1F3864")

    sub = doc.add_paragraph()
    r = sub.add_run("Executive Summary - Energy/Water/Food + Grid Resilience")
    r.font.size = Pt(13)
    r.font.color.rgb = RGBColor.from_string("404040")

    meta = doc.add_paragraph()
    meta_run = meta.add_run(
        f"Prepared: {date.today():%B %d, %Y}    |    Owner: Martin    |    "
        "Status: MVP / research preview"
    )
    meta_run.italic = True
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor.from_string("595959")
    _add_horizontal_rule(meta)

    # ---- 1. Purpose ---------------------------------------------------
    doc.add_heading("1. Purpose", level=1)
    doc.add_paragraph(
        "The Nexus Agent is an LLM-based research assistant that reasons "
        "across the Energy-Water-Food (E-W-F) nexus and electrical-grid "
        "resilience. Instead of running parallel manual searches on, for "
        "example, \"European energy price volatility\" and \"Lithium supply "
        "chains,\" an analyst asks the agent a single question. It performs "
        "the legwork - searching, citing, and synthesising - and returns a "
        "structured analysis plus a heat map of sectoral interdependencies "
        "in minutes."
    )

    # ---- 2. Architecture ---------------------------------------------
    doc.add_heading("2. Architecture", level=1)
    doc.add_paragraph(
        "The agent is built on LangGraph (state machine), langchain-openai "
        "(LLM + tool binding), and Tavily (web search). It packages cleanly "
        "into a Docker image that runs natively on Apple Silicon and Intel "
        "Macs."
    )

    doc.add_heading("2.1 Reasoning loop", level=2)
    doc.add_paragraph(
        "The workflow is the canonical Think -> Act -> Observe -> Repeat "
        "loop, augmented with a human-in-the-loop checkpoint:"
    )
    _add_bullets(doc, [
        "think  - the LLM either proposes tool calls or writes the final answer.",
        "human  - if HUMAN_IN_THE_LOOP=1, the operator can approve, edit, or skip the proposed tool calls.",
        "act    - executes approved tools (tavily_search, load_local_dataset, interdependency_lookup).",
        "answer - terminal node returning the synthesised, source-cited answer.",
        "Hard cap of 6 iterations prevents runaway loops.",
    ])

    doc.add_heading("2.2 Persona", level=2)
    p = doc.add_paragraph()
    p.add_run(
        "You are a Global Energy Nexus Expert. Your goal is to analyze how a "
        "disruption in one sector (like a cyberattack on a power grid) ripples "
        "into others (water treatment, transport). Always cite your sources."
    ).italic = True

    # ---- 3. Demo scenarios -------------------------------------------
    doc.add_heading("3. Demo scenarios", level=1)
    doc.add_paragraph(
        "Two presets ship with the MVP and are selectable from the CLI "
        "(--scenario data_center_water | grid_cyberattack | custom)."
    )
    _add_table(
        doc,
        headers=["Scenario", "Question", "Sectors in focus"],
        rows=[
            [
                "data_center_water",
                "How does current US data center demand affect water scarcity? Quantify direct and indirect withdrawals; identify the three most acute regions.",
                "energy, water, data centers",
            ],
            [
                "grid_cyberattack",
                "A coordinated cyberattack disables 15% of regional generation for 72h. Walk through cascading impacts and the two highest-leverage mitigations.",
                "grid, water, food, transport, comms",
            ],
        ],
        col_widths_inches=[1.6, 5.0, 1.7],
    )

    # ---- 4. Key findings ---------------------------------------------
    doc.add_heading("4. Key findings", level=1)

    doc.add_heading("4.1 Data centers vs. water scarcity", level=2)
    _add_bullets(doc, [
        "US data center electricity demand is on track to roughly double by 2030; AI-optimised facilities draw 5-10x the rack density of legacy enterprise sites (IEA, 2024).",
        "Direct cooling water at US data centers is on the order of 660 million gallons per day in 2024; indirect thermoelectric withdrawals through grid generation add an order of magnitude more (LBNL, 2024).",
        "Northern Virginia, Phoenix AZ, and Dallas TX are the three hubs where water stress and concentrated DC build-out collide most acutely.",
        "Thermoelectric power generation is ~41% of all US freshwater withdrawals (USGS); shifting marginal new load to dry-cooled or renewable assets is therefore disproportionately impactful in arid basins.",
    ])

    doc.add_heading("4.2 Grid cyberattack cascades", level=2)
    _add_table(
        doc,
        headers=["T+ (hours)", "Cascading event"],
        rows=[
            ["0-4",  "Generation loss begins; load shedding; cold-chain temperature drift starts."],
            ["4-8",  "Retail cold-chain losses accumulate; telecom batteries entering depletion."],
            ["8-24", "Cell sites drop in widening areas; payments, dispatch, and logistics degrade."],
            ["24-48","Water-utility on-site generators run low on fuel; boil-water notices issued."],
            ["48-72","Wastewater spills follow; fuel-logistics seizes up; EMS strain rises."],
        ],
        col_widths_inches=[1.4, 6.9],
    )
    doc.add_paragraph(
        "Highest-leverage mitigations identified by the agent: (1) black-start "
        "and dual-feed hardening for water and wastewater utilities, and "
        "(2) site new data center load on dry-cooled or renewable generation "
        "in water-stressed basins."
    )

    doc.add_heading("4.3 Interdependency heat map (excerpt)", level=2)
    doc.add_paragraph(
        "Coupling strengths in [0,1]; symmetric where bidirectional. Source: "
        "data/interdependencies.csv (illustrative starting matrix)."
    )
    _add_table(
        doc,
        headers=["Sector A", "Sector B", "Coupling", "Direction"],
        rows=[
            ["electricity", "data_centers", "0.95", "bidirectional"],
            ["electricity", "comms",        "0.90", "a -> b"],
            ["electricity", "water",        "0.85", "bidirectional"],
            ["water",       "food",         "0.80", "a -> b"],
            ["data_centers","comms",        "0.80", "bidirectional"],
            ["electricity", "food",         "0.70", "a -> b"],
            ["electricity", "transport",    "0.65", "a -> b"],
            ["food",        "transport",    "0.60", "bidirectional"],
            ["water",       "data_centers", "0.55", "a -> b"],
        ],
        col_widths_inches=[1.7, 1.7, 1.4, 3.5],
    )

    # ---- 5. MVP packaging --------------------------------------------
    doc.add_heading("5. MVP packaging", level=1)
    _add_bullets(doc, [
        "Repository layout: src/ (agent, tools, persona, heatmap, cli) + data/ (CSVs and scenarios.json) + reports/ (run outputs) + Dockerfile + docker-compose.yml.",
        "Run with: docker compose run --rm nexus-agent --scenario <preset> --heatmap.",
        "Native Python alternative: ./scripts/run_local.sh <preset> creates a .venv and runs without Docker.",
        "Mock mode is the default - no API keys required - so reviewers can run the demo offline.",
        "Live mode activates automatically when OPENAI_API_KEY and TAVILY_API_KEY are set in .env.",
        "Each run writes reports/run_<scenario>.json (full trace + final answer) and an interdependency heat map (.txt + .png).",
    ])

    # ---- 6. Recommendations ------------------------------------------
    doc.add_heading("6. Recommendations", level=1)
    _add_bullets(doc, [
        "Pilot the agent on three to five real research questions a week and compare time-to-answer against the current manual process; target a 5x speed-up.",
        "Replace the illustrative interdependencies.csv with a vetted matrix sourced from CISA Sector Risk Management Agencies and DOE/PNNL nexus studies before any external use.",
        "Add a second human-in-the-loop checkpoint at the answer step for high-stakes deliverables (regulatory filings, board memos).",
        "Wire LangSmith or OpenTelemetry tracing for evaluation - cost, latency, tool-call quality - before scaling beyond the MVP.",
        "Treat the model output as a draft. AI can make mistakes; double-check responses against the cited primary sources.",
    ])

    # ---- 7. Risks & caveats ------------------------------------------
    doc.add_heading("7. Risks and caveats", level=1)
    _add_bullets(doc, [
        "Numbers in the canned corpus (e.g. 660 Mgal/day, 41% withdrawals) are within publicly reported ranges but should be re-verified against primary sources before quoting externally.",
        "Tavily-only retrieval biases toward English-language, web-indexed material; supplement with internal knowledge bases for procurement-specific work.",
        "Mock mode produces a deterministic answer for demo purposes; do not interpret the mock output as a real research finding.",
        "API costs are bounded by MAX_ITERATIONS=6 but should still be metered in production deployments.",
    ])

    # ---- 8. Next steps -----------------------------------------------
    doc.add_heading("8. Next steps", level=1)
    _add_table(
        doc,
        headers=["#", "Action", "Owner", "Target"],
        rows=[
            ["1", "Stand up the Docker image on a developer Mac and run both demo scenarios.",     "Eng",       "Week 1"],
            ["2", "Curate v1 of interdependencies.csv from CISA + DOE/PNNL.",                       "Research",  "Week 2"],
            ["3", "Add LangSmith tracing and a small eval set (10 gold Q/A).",                      "Eng",       "Week 3"],
            ["4", "Pilot with two analysts; collect feedback on persona + tool surface.",          "Product",   "Week 4"],
            ["5", "Decide go/no-go on broader rollout.",                                            "Leadership","Week 6"],
        ],
        col_widths_inches=[0.5, 5.4, 1.2, 1.2],
    )

    # ---- 9. Sources ---------------------------------------------------
    doc.add_heading("9. Sources cited by the agent", level=1)
    _add_bullets(doc, [
        "IEA - Electricity 2024 outlook (data center demand projection).",
        "LBNL - 2024 United States Data Center Energy Usage Report (water use).",
        "USGS - Estimated Use of Water in the United States.",
        "CISA - Cross-Sector Cybersecurity Performance Goals.",
        "GAO-22-104746 - Colonial Pipeline ransomware lessons learned.",
        "FAO - Water for food security and nutrition.",
        "FERC/NERC - Final Report on the February 2021 Cold Weather Outages.",
    ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
