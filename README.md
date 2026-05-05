# Nexus Agent

A LangGraph-based agent that reasons across the **Energy-Water-Food nexus**
and **electrical grid resilience**. It uses the classic Think -> Act ->
Observe -> Repeat loop, with a human-in-the-loop checkpoint before any
tool call, and an OpenAI + Tavily search backend.

> **Persona**: *"You are a Global Energy Nexus Expert. Your goal is to
> analyze how a disruption in one sector (like a cyberattack on a power
> grid) ripples into others (water treatment, transport). Always cite
> your sources."*

## What's in the box

```
nexus-agent/
├── src/
│   ├── agent.py          # LangGraph state machine
│   ├── tools.py          # Tavily + local-data tools (with mock fallback)
│   ├── persona.py        # System prompt + scenario presets
│   ├── heatmap.py        # Renders the interdependency heat map
│   └── cli.py            # CLI entry point
├── data/                 # Sample CSV + scenario JSON
├── reports/              # Generated runs + heat-map images
├── scripts/              # Helper shell scripts
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Two run modes

| Mode | When | Needs API keys? |
|---|---|---|
| **Mock** (default) | Reviewers, offline demos, CI | No |
| **Live** | Real research | `OPENAI_API_KEY` + `TAVILY_API_KEY` in `.env` |

Mock mode ships a small canned corpus (IEA, LBNL, USGS, CISA, GAO, FAO,
FERC) and a deterministic ReAct trajectory, so the full LangGraph state
machine is exercised even without network or keys.

## Quick start (Docker, Mac)

```bash
cd nexus-agent
cp .env.example .env             # optional: add API keys for live mode
docker compose build
docker compose run --rm nexus-agent --scenario data_center_water --heatmap
docker compose run --rm nexus-agent --scenario grid_cyberattack   --heatmap
```

Or use the all-in-one helper:

```bash
./scripts/build_and_run.sh
```

## Quick start (native Python)

```bash
./scripts/run_local.sh data_center_water
./scripts/run_local.sh grid_cyberattack
```

## Custom questions + human-in-the-loop

```bash
HUMAN_IN_THE_LOOP=1 python -m src.cli \
  --question "How does a 30% drop in Sierra snowpack ripple into the WECC grid and Central Valley food output?"
```

At every tool round you'll get a prompt:

```
--- HUMAN-IN-THE-LOOP CHECKPOINT ---
  [0] tavily_search({'query': '...'})
approve/skip/edit (Enter | s | e <text>):
```

* `Enter`  approve
* `s`      skip this round (force the LLM to answer)
* `e <q>`  rewrite the search query

## The reasoning loop

```
START -> think -> [tool calls?] -> human -> act -> think -> ... -> answer -> END
                                            (approve / edit / skip)
```

* **think** - LLM picks a tool or writes the final answer
* **human** - optional review of the proposed tool calls
* **act**   - executes approved tools (`tavily_search`, `load_local_dataset`,
              `interdependency_lookup`)
* **answer**- terminal node returning the synthesised answer

Hard cap of 6 iterations to prevent runaway loops.

## Outputs

Each run writes:

* `reports/run_<scenario>.json` - full trace + final answer
* `reports/interdependency_heatmap.txt` - ASCII heat map
* `reports/interdependency_heatmap.png` - matplotlib heat map (if installed)

## Notes on accuracy

The mock corpus and CSVs are illustrative starting points, not vetted
references. Numbers (e.g. "660 Mgal/day", "41% of US water withdrawals")
are drawn from publicly reported ranges but should be re-verified against
the underlying primary sources before quoting in any external work.

> AI can make mistakes - double-check responses.
