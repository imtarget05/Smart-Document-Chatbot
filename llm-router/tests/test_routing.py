from dataclasses import replace

from app.config import Settings
from app.models import ChatRequest
from app.routing import choose_route


BASE_SETTINGS = Settings(
    local_base_url="http://local",
    local_model="llama3.2:3b",
    anthropic_api_key="test",
    anthropic_model="claude-test",
    openai_api_key="test",
    vision_model="gpt-4o",
)


def request(**routing):
    return ChatRequest(
        messages=[{"role": "user", "content": "What is the payment date?"}],
        routing=routing,
    )


def test_visual_input_has_highest_priority():
    decision = choose_route(
        request(has_image=True, document_count=8, task_type="compare"), BASE_SETTINGS
    )
    assert decision.provider == "openai"
    assert decision.reason == "visual_input"


def test_ollama_images_are_detected():
    payload = ChatRequest(
        messages=[{"role": "user", "content": "Read this", "images": ["base64"]}]
    )
    assert choose_route(payload, BASE_SETTINGS).provider == "openai"


def test_structured_scan_attachment_routes_to_vision():
    payload = request(attachments=[{"filename": "invoice.pdf", "is_scan": True}])
    decision = choose_route(payload, BASE_SETTINGS)
    assert decision.provider == "openai"
    assert decision.reason == "visual_input"


def test_structured_image_mime_type_routes_to_vision():
    payload = request(
        attachments=[{"filename": "upload.bin", "content_type": "image/png"}]
    )
    assert choose_route(payload, BASE_SETTINGS).provider == "openai"


def test_more_than_two_documents_routes_to_claude():
    decision = choose_route(request(document_count=3), BASE_SETTINGS)
    assert decision.provider == "anthropic"
    assert decision.reason == "document_count_gt_2"


def test_document_count_is_inferred_from_legacy_crag_prompt():
    payload = ChatRequest(
        messages=[
            {
                "role": "user",
                "content": "[contract-a.pdf] A\n[contract-b.pdf] B\n[contract-c.pdf] C\nQuestion: compare",
            }
        ]
    )
    decision = choose_route(payload, BASE_SETTINGS)
    assert decision.provider == "anthropic"
    assert decision.reason == "complex_task:compare"


def test_more_than_ten_pages_routes_to_claude():
    decision = choose_route(request(page_count=11), BASE_SETTINGS)
    assert decision.provider == "anthropic"
    assert decision.reason == "page_count_gt_10"


def test_compare_routes_to_claude():
    decision = choose_route(request(task_type="compare"), BASE_SETTINGS)
    assert decision.provider == "anthropic"


def test_low_confidence_escalates_before_local_call():
    decision = choose_route(request(confidence_score=0.69), BASE_SETTINGS)
    assert decision.provider == "anthropic"
    assert decision.escalated is True
    assert decision.reason == "low_confidence:0.690"


def test_threshold_is_inclusive_for_local():
    configured = replace(BASE_SETTINGS, confidence_threshold=0.7)
    decision = choose_route(
        request(confidence_score=0.7, task_type="extract_field"), configured
    )
    assert decision.provider == "local"
    assert decision.reason == "cost_optimized:extract_field"
