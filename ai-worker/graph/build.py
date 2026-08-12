from __future__ import annotations

from typing import Callable

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from nats.js import JetStreamContext

from graph.nodes.context_retrieval import make_context_retrieval_node
from graph.nodes.llm_reasoning import make_llm_reasoning_node
from graph.nodes.structured_output import make_structured_output_node
from graph.nodes.technical_check import technical_check
from graph.state import AnalysisState
from storage.cache import SentimentCache
from storage.postgres import PostgresStore


def _route_after_technical_check(state: AnalysisState) -> str:
    return "skip" if state.get("analysis") is not None else "continue"


def build_graph(
    postgres: PostgresStore,
    js: JetStreamContext,
    llm_client: ChatOpenAI,
    cache: SentimentCache,
    model_name: str,
    on_llm_call_result: Callable[[bool], None] | None = None,
):
    graph = StateGraph(AnalysisState)

    graph.add_node("technical_check", technical_check)
    graph.add_node("context_retrieval", make_context_retrieval_node(postgres, js))
    graph.add_node(
        "llm_reasoning",
        make_llm_reasoning_node(llm_client, cache, model_name, on_llm_call_result),
    )
    graph.add_node("structured_output", make_structured_output_node(js))

    graph.set_entry_point("technical_check")
    graph.add_conditional_edges(
        "technical_check",
        _route_after_technical_check,
        {"skip": END, "continue": "context_retrieval"},
    )
    graph.add_edge("context_retrieval", "llm_reasoning")
    graph.add_edge("llm_reasoning", "structured_output")
    graph.add_edge("structured_output", END)

    return graph.compile()
