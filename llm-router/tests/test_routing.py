from app.config import Settings
from app.models import ChatRequest
from app.routing import choose_route

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

BASE_SETTINGS = Settings(
    cloudflare_chat_model=MODEL,
)


def request(**routing):
    return ChatRequest(
        messages=[{"role": "user", "content": "What is the payment date?"}],
        routing=routing,
    )


def test_simple_qa_uses_cloudflare_model():
    decision = choose_route(request(), BASE_SETTINGS)
    assert decision.provider == "cloudflare"
    assert decision.model == MODEL
    assert decision.reason == "simple_task:qa"


def test_extract_task_uses_cloudflare_model():
    decision = choose_route(request(task_type="extract_field"), BASE_SETTINGS)
    assert decision.model == MODEL
    assert decision.reason == "simple_task:extract_field"


def test_compare_uses_cloudflare_model():
    decision = choose_route(request(task_type="compare"), BASE_SETTINGS)
    assert decision.model == MODEL
    assert decision.reason == "complex_task:compare"


def test_summarize_uses_cloudflare_model():
    decision = choose_route(request(task_type="summarize"), BASE_SETTINGS)
    assert decision.model == MODEL


def test_more_than_two_documents_uses_cloudflare_model():
    decision = choose_route(request(document_count=3), BASE_SETTINGS)
    assert decision.model == MODEL
    assert decision.reason == "complex_task:qa"


def test_more_than_ten_pages_uses_cloudflare_model():
    decision = choose_route(request(page_count=11), BASE_SETTINGS)
    assert decision.model == MODEL


def test_task_type_inferred_from_text():
    payload = ChatRequest(
        messages=[{"role": "user", "content": "Compare contract A and B"}]
    )
    decision = choose_route(payload, BASE_SETTINGS)
    assert decision.task_type == "compare"
    assert decision.model == MODEL


def test_low_confidence_records_reason():
    decision = choose_route(request(confidence_score=0.69), BASE_SETTINGS)
    assert decision.model == MODEL
    assert decision.reason == "low_confidence:0.690"


def test_confidence_at_threshold_stays_simple():
    decision = choose_route(
        request(confidence_score=0.7, task_type="extract_field"), BASE_SETTINGS
    )
    assert decision.model == MODEL
    assert decision.reason == "simple_task:extract_field"


def test_high_confidence_compare_remains_complex():
    decision = choose_route(
        request(confidence_score=0.95, task_type="compare"), BASE_SETTINGS
    )
    assert decision.model == MODEL
    assert decision.reason == "complex_task:compare"