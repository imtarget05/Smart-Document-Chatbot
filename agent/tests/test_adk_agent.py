from adk_agent import AdkAgent, AdkAgentSpec


def test_adk_agent_returns_structured_response():
    spec = AdkAgentSpec(
        name="document-analyst",
        description="Summarizes a document for the 5-day demo",
        instructions="Return a short bullet summary.",
    )
    agent = AdkAgent(spec)

    result = agent.run("Explain why the project is a good ADK candidate.")

    assert result["agent"] == "document-analyst"
    assert result["status"] == "ok"
    assert "input" in result
