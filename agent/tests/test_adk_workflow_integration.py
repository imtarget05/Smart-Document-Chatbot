from graph.workflow import run_adk_demo_node


def test_run_adk_demo_node_populates_state():
    state = {
        "query": "Summarize the incident report",
        "session_id": "session-1",
        "user_id": "user-1",
        "document_ids": [],
        "messages": [],
        "long_term_history": [],
        "retrieved_chunks": [],
        "confidence_score": 0.0,
        "hybrid_search_enabled": True,
        "agent_plan": "",
        "agent_type": "adk",
        "intent_override": None,
        "use_web_search": False,
        "final_answer": "",
        "sources": [],
        "action_result": None,
        "report_path": None,
    }

    result = run_adk_demo_node(state)

    assert result["agent_type"] == "adk"
    assert result["final_answer"].startswith("ADK Demo")
    assert result["trace"]["step_count"] == 5
