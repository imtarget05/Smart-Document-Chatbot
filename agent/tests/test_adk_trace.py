from adk_runtime import run_demo_workflow


def test_trace_metadata_is_attached_to_workflow_result():
    result = run_demo_workflow("Summarize the incident", "incident.pdf")

    assert result["trace"]["status"] == "ok"
    assert result["trace"]["step_count"] == 5
