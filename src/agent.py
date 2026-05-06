"""LangGraph state machine for the Nexus Agent.

Workflow (the Reasoning Loop):

    ┌────────────┐    no tool calls      ┌────────────┐
    │   think    │ ───────────────────►  │   answer   │
    │  (LLM)     │ ◄──────────────┐      └────────────┘
    └─────┬──────┘                │
          │ tool calls            │
          ▼                       │
    ┌────────────┐                │
    │   human    │ approve/edit   │
    │  in loop   │ ───────────────┘
    └─────┬──────┘
          │
          ▼
    ┌────────────┐
    │   act      │  (run tools)
    └─────┬──────┘
          │ observations
          ▼
       (back to think)

`think`  - LLM decides whether to call a tool or finalise.
`human`  - if HUMAN_IN_THE_LOOP=1, the workflow pauses and asks the user
            to approve, edit, or skip the proposed tool calls.
`act`    - executes approved tool calls.
`answer` - terminal node returning the final synthesised answer.
"""
from __future__ import annotations

import os
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .persona import NEXUS_SYSTEM_PROMPT
from .tools import ALL_TOOLS, make_llm, is_mock_mode


class NexusState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    iterations: int


MAX_ITERATIONS = 6  # safety guard against runaway loops


def _think_node(state: NexusState) -> NexusState:
    """LLM reasoning step. Returns either tool-calls or a final answer."""
    llm = make_llm()
    msgs = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in msgs):
        msgs = [SystemMessage(content=NEXUS_SYSTEM_PROMPT)] + list(msgs)
    ai = llm.invoke(msgs)
    return {"messages": [ai], "iterations": state.get("iterations", 0) + 1}


def _human_review_node(state: NexusState) -> NexusState:
    """Human-in-the-loop checkpoint.

    If HUMAN_IN_THE_LOOP=1 the agent pauses and prints the proposed tool
    calls. The operator can:
      [Enter]   - approve as-is
      s         - skip this tool round (force the model to answer)
      e <text>  - replace the query of the first tool call with <text>
    """
    if os.environ.get("HUMAN_IN_THE_LOOP", "0") != "1":
        return {"messages": []}

    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return {"messages": []}

    print("\n--- HUMAN-IN-THE-LOOP CHECKPOINT ---")
    for i, tc in enumerate(last.tool_calls):
        print(f"  [{i}] {tc['name']}({tc['args']})")
    choice = input("approve/skip/edit (Enter | s | e <text>): ").strip()

    if choice == "s":
        # Force termination by injecting an empty AIMessage with no tool calls.
        return {
            "messages": [AIMessage(content="(human skipped tool round)")],
        }
    if choice.startswith("e "):
        new_query = choice[2:].strip()
        edited = dict(last.tool_calls[0])
        edited["args"] = {**edited["args"], "query": new_query}
        # Replace the last AIMessage with edited tool calls.
        edited_ai = AIMessage(content=last.content, tool_calls=[edited] + list(last.tool_calls[1:]))
        return {"messages": [edited_ai]}

    return {"messages": []}  # approved as-is


def _route_after_think(state: NexusState) -> Literal["human", "answer", "stop"]:
    last = state["messages"][-1]
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return "stop"
    if isinstance(last, AIMessage) and last.tool_calls:
        return "human"
    return "answer"


def _route_after_human(state: NexusState) -> Literal["act", "answer"]:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "act"
    return "answer"


def _answer_node(state: NexusState) -> NexusState:
    """Terminal node - just passes the last message through."""
    return {"messages": []}


def build_graph():
    g = StateGraph(NexusState)
    g.add_node("think", _think_node)
    g.add_node("human", _human_review_node)
    g.add_node("act", ToolNode(ALL_TOOLS))
    g.add_node("answer", _answer_node)

    g.add_edge(START, "think")
    g.add_conditional_edges(
        "think",
        _route_after_think,
        {"human": "human", "answer": "answer", "stop": "answer"},
    )
    g.add_conditional_edges(
        "human",
        _route_after_human,
        {"act": "act", "answer": "answer"},
    )
    g.add_edge("act", "think")
    g.add_edge("answer", END)
    return g.compile()


def run_agent(question: str) -> str:
    """Run the agent end-to-end and return the final answer text."""
    graph = build_graph()
    initial: NexusState = {
        "messages": [HumanMessage(content=question)],
        "iterations": 0,
    }
    final = graph.invoke(initial)
    # Final answer is the last AIMessage with no tool calls.
    for msg in reversed(final["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            return msg.content
    return "(no answer produced)"


def trace_agent(question: str) -> list[dict]:
    """Run the agent and return a structured trace of every node transition.

    Useful for the demo - prints out the Think/Act/Observe loop visibly.
    """
    graph = build_graph()
    trace: list[dict] = []
    initial: NexusState = {
        "messages": [HumanMessage(content=question)],
        "iterations": 0,
    }
    for event in graph.stream(initial, stream_mode="updates"):
        for node_name, node_state in event.items():
            new_msgs = node_state.get("messages", []) if isinstance(node_state, dict) else []
            for m in new_msgs:
                trace.append(
                    {
                        "node": node_name,
                        "type": getattr(m, "type", type(m).__name__),
                        "content": (m.content[:300] if isinstance(m.content, str) else str(m.content)[:300]),
                        "tool_calls": getattr(m, "tool_calls", None),
                    }
                )
    return trace


__all__ = ["build_graph", "run_agent", "trace_agent", "is_mock_mode"]
