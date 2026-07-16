from adk_runtime import run_demo_workflow


def test_run_demo_workflow_returns_steps_and_summary():
    result = run_demo_workflow(
        user_request="Summarize the engineering report",
        document_name="sample-report.pdf",
    )

    assert result["status"] == "ok"
    assert result["document_name"] == "sample-report.pdf"
    assert len(result["steps"]) == 5
    assert any(step["name"] == "summarize" for step in result["steps"])
