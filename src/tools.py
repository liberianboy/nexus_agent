"""Tools exposed to the Nexus Agent.

The same tool surface works in two modes:

* Live mode: requires OPENAI_API_KEY and TAVILY_API_KEY in the environment.
  Uses langchain_openai.ChatOpenAI and the official Tavily search tool.

* Mock mode (default when keys are missing): a small canned corpus stands in
  for the web. This makes the demo runnable on a fresh machine with no
  network and no API keys, which is what most reviewers want for an MVP.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from langchain_core.tools import tool

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _have_live_keys() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY")) and bool(
        os.environ.get("TAVILY_API_KEY")
    )


# ---------------------------------------------------------------------------
# Mock corpus
# ---------------------------------------------------------------------------

_MOCK_CORPUS: List[Dict[str, str]] = [
    {
        "title": "US data center electricity use is set to more than double by 2030",
        "url": "https://www.iea.org/reports/electricity-2024",
        "content": (
            "The IEA projects global data center electricity consumption could "
            "reach 945 TWh by 2030, with the United States accounting for "
            "roughly half of the increase. AI-optimised facilities draw 5-10x "
            "the rack density of legacy enterprise data centers."
        ),
    },
    {
        "title": "Water consumption of US data centers - LBNL 2024",
        "url": "https://eta.lbl.gov/publications/2024-united-states-data-center",
        "content": (
            "Direct water use for cooling at US data centers is estimated at "
            "660 million gallons per day in 2024. Indirect thermoelectric "
            "withdrawals from grid power generation add an order of magnitude "
            "more. Northern Virginia, Phoenix AZ, and Dallas TX are flagged "
            "as the most water-stressed major hubs."
        ),
    },
    {
        "title": "USGS - Estimated Use of Water in the United States",
        "url": "https://www.usgs.gov/mission-areas/water-resources/science/water-use-united-states",
        "content": (
            "Thermoelectric power generation is the single largest category "
            "of US water withdrawals at ~41% of total. A 1% shift in the "
            "generation mix toward dry-cooled or renewable assets reduces "
            "withdrawals materially in arid regions."
        ),
    },
    {
        "title": "CISA - Cross-Sector Cyber Performance Goals",
        "url": "https://www.cisa.gov/cross-sector-cybersecurity-performance-goals",
        "content": (
            "Sustained loss of bulk power for >24 hours triggers cascading "
            "failures: water utilities exhaust on-site generator fuel within "
            "24-72 hours; municipal wastewater spills follow; cold chain "
            "losses begin at 4-8 hours; telecom central offices fail at "
            "8-72 hours depending on battery and generator depth."
        ),
    },
    {
        "title": "Colonial Pipeline lessons - GAO 2022",
        "url": "https://www.gao.gov/products/gao-22-104746",
        "content": (
            "The 2021 Colonial Pipeline ransomware incident showed how an IT "
            "compromise forced an OT-side shutdown, with fuel shortages "
            "rippling into trucking, aviation, and food distribution within "
            "72 hours."
        ),
    },
    {
        "title": "FAO - Water for food security and nutrition",
        "url": "https://www.fao.org/3/i9223en/I9223EN.pdf",
        "content": (
            "Agriculture accounts for ~70% of global freshwater withdrawals. "
            "Energy is required at every stage of the food chain: pumping, "
            "fertilizer (Haber-Bosch is gas-intensive), refrigeration, "
            "processing, and transport. Disruptions in electricity and "
            "natural gas markets propagate to food prices within 1-2 quarters."
        ),
    },
    {
        "title": "ERCOT February 2021 outage - root cause analysis",
        "url": "https://www.ferc.gov/news-events/news/ferc-nerc-staff-issue-final-report-feb-2021-cold-weather-outages",
        "content": (
            "The 2021 Texas grid event saw 4.5M customers lose power, water "
            "boil-notices issued for 14M people due to depressurized "
            "treatment plants, and grocery losses estimated at $600M-$1B. "
            "Natural-gas and electricity interdependence was the dominant "
            "failure mode."
        ),
    },
]


def _mock_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Naive bag-of-words ranker over the canned corpus."""
    q_terms = {t.lower() for t in query.split() if len(t) > 3}
    scored: List[tuple[int, Dict[str, str]]] = []
    for doc in _MOCK_CORPUS:
        hay = (doc["title"] + " " + doc["content"]).lower()
        score = sum(1 for t in q_terms if t in hay)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        scored = [(0, doc) for doc in _MOCK_CORPUS[:max_results]]
    return [doc for _, doc in scored[:max_results]]


# ---------------------------------------------------------------------------
# LangChain tool definitions
# ---------------------------------------------------------------------------


@tool
def tavily_search(query: str) -> str:
    """Search the web for up-to-date information on the energy-water-food nexus
    or grid resilience. Returns a JSON list of {title, url, content}."""
    if _have_live_keys():
        # Lazy import so mock-mode users don't need the package installed.
        from langchain_community.tools.tavily_search import TavilySearchResults

        live = TavilySearchResults(max_results=4)
        results = live.invoke({"query": query})
        return json.dumps(results, indent=2)
    return json.dumps(_mock_search(query), indent=2)


@tool
def load_local_dataset(name: str) -> str:
    """Load a curated CSV from the data/ directory by stem name
    (e.g. 'interdependencies', 'water_stress_by_region'). Returns CSV text."""
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        return f"ERROR: dataset '{name}' not found in {DATA_DIR}"
    return path.read_text()


@tool
def interdependency_lookup(sector_a: str, sector_b: str) -> str:
    """Return a coupling-strength score in [0,1] between two sectors,
    drawn from data/interdependencies.csv."""
    import csv

    path = DATA_DIR / "interdependencies.csv"
    if not path.exists():
        return "ERROR: interdependencies.csv not found"
    a, b = sector_a.lower().strip(), sector_b.lower().strip()
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["sector_a"].lower() == a and row["sector_b"].lower() == b:
                return json.dumps(row)
            if row["sector_a"].lower() == b and row["sector_b"].lower() == a:
                return json.dumps(row)
    return f"No coupling data for ({sector_a}, {sector_b})"


ALL_TOOLS = [tavily_search, load_local_dataset, interdependency_lookup]


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


@dataclass
class MockResponse:
    content: str
    tool_calls: list


class MockLLM:
    """Deterministic stand-in for ChatOpenAI.

    The mock follows a fixed Think -> Act -> Observe -> Repeat trajectory:
    it issues two tavily_search tool calls in turn, then writes a final
    answer that synthesises whatever the tool returned. That's enough to
    exercise the full LangGraph state machine offline.
    """

    def __init__(self) -> None:
        self._step = 0

    def bind_tools(self, _tools):  # langgraph expects this method
        return self

    def invoke(self, messages):
        from langchain_core.messages import AIMessage

        # Find the last human/system query for context.
        last_user = ""
        for m in reversed(messages):
            if getattr(m, "type", "") == "human":
                last_user = m.content
                break

        self._step += 1

        if self._step == 1:
            # First search: broad context.
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "tavily_search",
                        "args": {"query": last_user[:120] or "energy water food nexus"},
                        "id": f"call_{self._step}",
                    }
                ],
            )
        if self._step == 2:
            # Second search: cascading effects angle.
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "tavily_search",
                        "args": {
                            "query": "cascading effects "
                            + (last_user[:80] or "grid water food")
                        },
                        "id": f"call_{self._step}",
                    }
                ],
            )

        # Third turn: synthesise. Pull observation text out of recent
        # ToolMessages so the answer reflects what was "found".
        observations: list[str] = []
        for m in messages[-6:]:
            if getattr(m, "type", "") == "tool":
                observations.append(str(m.content)[:600])
        evidence = "\n\n".join(observations) or "(no observations)"

        synthesis = (
            "## Nexus Analysis\n\n"
            f"Question: {last_user.strip()}\n\n"
            "First-order linkages identified:\n"
            "- Electricity is the master utility: water treatment, food cold "
            "chain, comms, and transport fueling all depend on it.\n"
            "- Water enables ~41% of US power generation via thermoelectric "
            "cooling. Cuts run both ways.\n"
            "- Data centers are the fastest-growing electricity demand class "
            "and concentrate cooling water in already-stressed basins.\n\n"
            "Cascading effects (typical 0-72h horizon):\n"
            "- T+0-8h: cold chain losses begin; telecom batteries deplete.\n"
            "- T+24-72h: water-utility generators run out of fuel; boil "
            "notices spread; wastewater spills follow.\n"
            "- T+1-2 quarters: food-price and fertilizer markets price in "
            "the energy disruption.\n\n"
            "Highest-leverage mitigations:\n"
            "1. Black-start and dual-feed hardening for water and wastewater.\n"
            "2. Shift new data center load to dry-cooled or renewable "
            "generation in water-stressed basins (AZ, TX, NV).\n\n"
            "Evidence consulted (excerpts):\n"
            f"{evidence}\n\n"
            "Sources:\n"
            "[1] IEA Electricity 2024 - data center demand outlook.\n"
            "[2] LBNL 2024 - US data center water use.\n"
            "[3] USGS - thermoelectric water withdrawals.\n"
            "[4] CISA Cross-Sector CPGs - cascading-failure timelines.\n"
            "[5] FERC/NERC Feb 2021 cold-weather report (ERCOT).\n"
            "[domain knowledge] - standard nexus framing.\n"
        )
        return AIMessage(content=synthesis, tool_calls=[])


def make_llm(model: str = "gpt-4o-mini", temperature: float = 0.2):
    """Return a tool-bound LLM, falling back to MockLLM offline."""
    if _have_live_keys():
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature).bind_tools(ALL_TOOLS)
    return MockLLM().bind_tools(ALL_TOOLS)


def is_mock_mode() -> bool:
    return not _have_live_keys()
